import net = require('node:net');
import {
  Backend,
  BackendEvent,
  BreakpointRequest,
  BreakpointResult,
  DebugCore,
  LaunchConfig,
  RegisterValue,
  StackFrameInfo,
} from '../protocol';
import { profileFor } from '../c28x/registers';

class OpenOcdTelnetClient {
  private socket: any;
  private buffer = '';
  private readonly pending: Array<{ resolve: (text: string) => void; reject: (error: Error) => void }> = [];

  public async connect(host: string, port: number): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      this.socket = net.createConnection({ host, port }, resolve);
      this.socket.once('error', reject);
      this.socket.on('data', (data: Buffer) => this.handle(data.toString()));
      this.socket.on('close', () => {
        while (this.pending.length) {
          this.pending.shift()?.reject(new Error('OpenOCD telnet connection closed'));
        }
      });
    });
    await this.command('echo c2000-debug-ready');
  }

  public command(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
      this.pending.push({ resolve, reject });
      this.socket.write(`${command}\n`);
    });
  }

  public close(): void {
    this.socket?.end();
  }

  private handle(chunk: string): void {
    this.buffer += chunk.replace(/\r/g, '');
    const prompt = '> ';
    let index = this.buffer.indexOf(prompt);
    while (index >= 0) {
      const text = this.buffer.slice(0, index).trim();
      this.buffer = this.buffer.slice(index + prompt.length);
      this.pending.shift()?.resolve(text);
      index = this.buffer.indexOf(prompt);
    }
  }
}

export class OpenOcdBackend implements Backend {
  private readonly telnet = new OpenOcdTelnetClient();
  private readonly listeners: Array<(event: BackendEvent) => void> = [];
  private activeCores: DebugCore[] = [];
  private config?: LaunchConfig;
  private breakpointIds: number[] = [];

  public async start(config: LaunchConfig): Promise<DebugCore[]> {
    this.config = config;
    await this.telnet.connect(config.openocdHost ?? '127.0.0.1', config.openocdTelnetPort ?? 4444);
    this.activeCores = [{
      id: 1,
      name: config.corePattern ?? config.device,
      architecture: config.device.endsWith('_m3') ? 'cortex-m3' : 'c28x',
      device: config.device,
      addressScale: config.addressScale ?? (config.device.endsWith('_m3') ? 1 : 2),
    }];
    await this.telnet.command('halt');
    this.emit({ event: 'stopped', coreId: 1, reason: 'entry' });
    return this.activeCores;
  }

  public async stop(_terminate: boolean): Promise<void> {
    this.telnet.close();
  }

  public cores(): DebugCore[] {
    return this.activeCores;
  }

  public async continue(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    await this.telnet.command('resume');
    this.emit({ event: 'continued', coreId });
  }

  public async halt(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    await this.telnet.command('halt');
    this.emit({ event: 'stopped', coreId, reason: 'pause' });
  }

  public async step(coreId: number, _kind: 'into' | 'over' | 'out' | 'instruction'): Promise<void> {
    this.ensureCore(coreId);
    await this.telnet.command('step');
    this.emit({ event: 'stopped', coreId, reason: 'step' });
  }

  public async reset(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    await this.telnet.command('reset halt');
    this.emit({ event: 'stopped', coreId, reason: 'restart' });
  }

  public async stack(coreId: number): Promise<StackFrameInfo[]> {
    this.ensureCore(coreId);
    const pc = await this.readNamedRegister('pc');
    return [{ id: 1001, name: '<OpenOCD instruction frame>', pc }];
  }

  public async registers(coreId: number): Promise<RegisterValue[]> {
    this.ensureCore(coreId);
    const output = await this.telnet.command('reg');
    const values = new Map<string, bigint>();
    for (const line of output.split('\n')) {
      const match = line.match(/^\s*\(?\d+\)?\s*([A-Za-z][A-Za-z0-9_]*)\s*\(.*?\):\s*(0x[0-9a-f]+)/i)
        ?? line.match(/^\s*([A-Za-z][A-Za-z0-9_]*)\s+.*?(0x[0-9a-f]+)\s*$/i);
      if (match) {
        values.set(match[1].toUpperCase(), BigInt(match[2]));
      }
    }
    const core = this.activeCores[0];
    return profileFor(core.device, core.architecture, this.config?.registerProfile).map((definition) => ({
      name: definition.name,
      value: values.get(definition.name.toUpperCase()) ?? 0n,
      bits: definition.bits,
      group: definition.group,
    }));
  }

  public async writeRegister(coreId: number, name: string, value: bigint): Promise<void> {
    this.ensureCore(coreId);
    await this.telnet.command(`reg ${name} 0x${value.toString(16)}`);
  }

  public async evaluate(coreId: number, expression: string): Promise<string> {
    this.ensureCore(coreId);
    if (/^[A-Za-z][A-Za-z0-9_]*$/.test(expression)) {
      return `0x${(await this.readNamedRegister(expression)).toString(16)}`;
    }
    throw new Error('OpenOCD backend evaluation currently supports register names only');
  }

  public async readMemory(coreId: number, byteAddress: bigint, byteCount: number): Promise<Buffer> {
    this.ensureCore(coreId);
    const output = Buffer.alloc(byteCount);
    let completed = 0;
    while (completed < byteCount) {
      const count = Math.min(64, byteCount - completed);
      const response = await this.telnet.command(`mdb 0x${(byteAddress + BigInt(completed)).toString(16)} ${count}`);
      const bytes = [...response.matchAll(/(?:^|\s)([0-9a-f]{2})(?=\s|$)/gi)].map((match) => Number.parseInt(match[1], 16));
      if (bytes.length < count) {
        throw new Error(`OpenOCD returned ${bytes.length} bytes, expected ${count}: ${response}`);
      }
      Buffer.from(bytes.slice(0, count)).copy(output, completed);
      completed += count;
    }
    return output;
  }

  public async writeMemory(coreId: number, byteAddress: bigint, data: Buffer): Promise<number> {
    this.ensureCore(coreId);
    for (let index = 0; index < data.length; index += 1) {
      await this.telnet.command(`mwb 0x${(byteAddress + BigInt(index)).toString(16)} 0x${data[index].toString(16)}`);
    }
    return data.length;
  }

  public async setBreakpoints(coreId: number, breakpoints: BreakpointRequest[]): Promise<BreakpointResult[]> {
    this.ensureCore(coreId);
    for (const address of this.breakpointIds) {
      await this.telnet.command(`rbp 0x${address.toString(16)}`);
    }
    this.breakpointIds = [];
    const results: BreakpointResult[] = [];
    for (let index = 0; index < breakpoints.length; index += 1) {
      const breakpoint = breakpoints[index];
      if (breakpoint.address === undefined) {
        results.push({ id: index + 1, verified: false, line: breakpoint.line, message: 'OpenOCD telnet requires instruction addresses' });
        continue;
      }
      const address = Number(breakpoint.address);
      await this.telnet.command(`bp 0x${address.toString(16)} 2 hw`);
      this.breakpointIds.push(address);
      results.push({ id: index + 1, verified: true, line: breakpoint.line });
    }
    return results;
  }

  public onEvent(listener: (event: BackendEvent) => void): void {
    this.listeners.push(listener);
  }

  private async readNamedRegister(name: string): Promise<bigint> {
    const output = await this.telnet.command(`reg ${name}`);
    const match = output.match(/0x[0-9a-f]+/i);
    if (!match) {
      throw new Error(`unable to parse register ${name}: ${output}`);
    }
    return BigInt(match[0]);
  }

  private ensureCore(coreId: number): void {
    if (coreId !== 1) {
      throw new Error(`OpenOCD backend exposes one core, requested ${coreId}`);
    }
  }

  private emit(event: BackendEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
