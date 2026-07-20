import childProcess = require('node:child_process');
import net = require('node:net');
import path = require('node:path');
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
import { AddressTranslator } from '../c28x/addressing';

interface PendingCommand {
  command: string;
  resolve: (text: string) => void;
  reject: (error: Error) => void;
  timer: any;
}

interface RenodeRegister {
  name: string;
  index: number;
  bits: number;
  group: string;
}

// This mirrors the register mapping implemented by xsession/renode-infrastructure
// for the custom C2000 core. Keep it explicit: Renode currently exposes no
// GDB target-description features for this architecture.
const RENODE_C2000_REGISTERS: RenodeRegister[] = [
  { name: 'ACC', index: 0, bits: 32, group: 'Core' },
  { name: 'AH', index: 1, bits: 16, group: 'Core aliases' },
  { name: 'AL', index: 2, bits: 16, group: 'Core aliases' },
  { name: 'P', index: 3, bits: 32, group: 'Core' },
  { name: 'PH', index: 4, bits: 16, group: 'Core aliases' },
  { name: 'PL', index: 5, bits: 16, group: 'Core aliases' },
  { name: 'XT', index: 6, bits: 32, group: 'Core' },
  { name: 'T', index: 7, bits: 16, group: 'Core aliases' },
  ...Array.from({ length: 8 }, (_, index) => ({
    name: `XAR${index}`,
    index: 8 + index,
    bits: 32,
    group: 'Address',
  })),
  ...Array.from({ length: 8 }, (_, index) => ({
    name: `AR${index}`,
    index: 16 + index,
    bits: 16,
    group: 'Address aliases',
  })),
  { name: 'SP', index: 24, bits: 16, group: 'Address' },
  { name: 'PC', index: 25, bits: 32, group: 'Control' },
  { name: 'RPC', index: 26, bits: 32, group: 'Control' },
  { name: 'ST0', index: 27, bits: 16, group: 'Status' },
  { name: 'ST1', index: 28, bits: 16, group: 'Status' },
  { name: 'IFR', index: 29, bits: 16, group: 'Status' },
  { name: 'IER', index: 30, bits: 16, group: 'Status' },
  { name: 'DP', index: 31, bits: 16, group: 'Address' },
];

class RenodeMonitorClient {
  private socket: any;
  private buffer = '';
  private connected = false;
  private readyResolve?: () => void;
  private readyReject?: (error: Error) => void;
  private readonly queue: PendingCommand[] = [];
  private active?: PendingCommand;

  public async connect(host: string, port: number, timeoutMs: number): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Renode monitor did not become ready at ${host}:${port}`));
        this.socket?.destroy();
      }, timeoutMs);
      this.readyResolve = () => {
        clearTimeout(timer);
        this.connected = true;
        resolve();
      };
      this.readyReject = (error) => {
        clearTimeout(timer);
        reject(error);
      };
      this.socket = net.createConnection({ host, port });
      this.socket.on('data', (data: Buffer) => this.handle(data));
      this.socket.once('error', (error: Error) => {
        if (!this.connected) {
          this.readyReject?.(error);
        }
        this.failAll(error);
      });
      this.socket.on('close', () => {
        this.connected = false;
        this.failAll(new Error('Renode monitor connection closed'));
      });
    });
  }

  public command(command: string, timeoutMs = 5000): Promise<string> {
    if (!this.connected) {
      return Promise.reject(new Error('Renode monitor is not connected'));
    }
    return new Promise((resolve, reject) => {
      const pending: PendingCommand = {
        command,
        resolve,
        reject,
        timer: setTimeout(() => {
          if (this.active === pending) {
            this.active = undefined;
          } else {
            const index = this.queue.indexOf(pending);
            if (index >= 0) this.queue.splice(index, 1);
          }
          reject(new Error(`Renode monitor command timed out: ${command}`));
          this.pump();
        }, timeoutMs),
      };
      this.queue.push(pending);
      this.pump();
    });
  }

  public close(): void {
    this.connected = false;
    this.socket?.end();
  }

  private pump(): void {
    if (!this.connected || this.active || !this.queue.length) {
      return;
    }
    this.active = this.queue.shift();
    this.socket.write(`${this.active?.command}\n`);
  }

  private handle(data: Buffer): void {
    const decoded = data.toString('utf8')
      .replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, '')
      .replace(/\xff[\x00-\xff]{0,2}/g, '')
      .replace(/\r/g, '');
    this.buffer += decoded;

    // Renode prompts are `(monitor) ` before a machine is selected and
    // `(machine-name) ` afterwards. A prompt marks completion of one command.
    const prompt = /(?:^|\n)\([^)\n]+\)\s*$/;
    const match = this.buffer.match(prompt);
    if (!match || match.index === undefined) {
      return;
    }
    const prefixLength = match[0].startsWith('\n') ? 1 : 0;
    const outputEnd = match.index + prefixLength;
    const output = this.buffer.slice(0, outputEnd);
    this.buffer = '';

    if (!this.connected) {
      this.readyResolve?.();
      return;
    }
    if (!this.active) {
      return;
    }
    const current = this.active;
    this.active = undefined;
    clearTimeout(current.timer);
    current.resolve(this.cleanOutput(output, current.command));
    this.pump();
  }

  private cleanOutput(output: string, command: string): string {
    const lines = output.split('\n');
    const commandIndex = lines.findIndex((line) => line.trim() === command.trim());
    if (commandIndex >= 0) {
      lines.splice(commandIndex, 1);
    }
    return lines.join('\n').trim();
  }

  private failAll(error: Error): void {
    if (this.active) {
      clearTimeout(this.active.timer);
      this.active.reject(error);
      this.active = undefined;
    }
    while (this.queue.length) {
      const pending = this.queue.shift();
      if (pending) {
        clearTimeout(pending.timer);
        pending.reject(error);
      }
    }
  }
}

export class RenodeBackend implements Backend {
  private monitor = new RenodeMonitorClient();
  private readonly listeners: Array<(event: BackendEvent) => void> = [];
  private activeCores: DebugCore[] = [];
  private config?: LaunchConfig;
  private process?: any;
  private translator = new AddressTranslator(2);
  private breakpointAddresses: bigint[] = [];
  private stopPoll?: any;
  private stopping = false;

  public async start(config: LaunchConfig): Promise<DebugCore[]> {
    this.config = config;
    this.translator = new AddressTranslator(config.addressScale ?? 2);
    const host = config.renodeHost ?? '127.0.0.1';
    const port = config.renodeMonitorPort ?? 1234;
    const timeoutMs = config.renodeStartupTimeoutMs ?? 15000;

    const shouldSpawn = config.renodeLaunch ?? config.request !== 'attach';
    if (shouldSpawn) {
      if (!config.renodePath) {
        throw new Error('renodePath is required when renodeLaunch is true');
      }
      this.spawnRenode(config.renodePath, port, config.renodeArgs ?? []);
    }

    await this.connectWithRetry(host, port, timeoutMs);
    if (config.renodeScript) {
      await this.command(`include @${this.pathLiteral(config.renodeScript)}`, timeoutMs);
    }
    if (config.renodeMachine) {
      await this.command(`mach set ${this.stringLiteral(config.renodeMachine)}`);
    }

    this.activeCores = [{
      id: 1,
      name: config.renodeCpu ?? 'cpu',
      architecture: 'c28x',
      device: config.device,
      addressScale: config.addressScale ?? 2,
    }];

    await this.command('pause');
    if (config.request !== 'attach' && config.executable && config.renodeLoadExecutable !== false) {
      await this.loadExecutable(config.executable);
    }
    if (config.renodeEntryAddress !== undefined) {
      await this.writeRegister(1, 'PC', this.parseConfigInteger(config.renodeEntryAddress));
    }
    await this.setCpuHalted(true, false);
    setTimeout(() => this.emit({ event: 'stopped', coreId: 1, reason: 'entry' }), 0);
    return this.activeCores;
  }

  public async stop(terminate: boolean): Promise<void> {
    this.stopping = true;
    this.stopPolling();
    this.monitor.close();
    if (this.process && terminate) {
      this.process.kill('SIGTERM');
    }
    this.process = undefined;
    this.activeCores = [];
  }

  public cores(): DebugCore[] {
    return this.activeCores;
  }

  public async continue(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    await this.setCpuHalted(false, false);
    await this.command('start');
    this.emit({ event: 'continued', coreId });
    this.startPolling(coreId);
  }

  public async halt(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    this.stopPolling();
    await this.command('pause');
    await this.setCpuHalted(true, false);
    this.emit({ event: 'stopped', coreId, reason: 'pause' });
  }

  public async step(coreId: number, _kind: 'into' | 'over' | 'out' | 'instruction'): Promise<void> {
    this.ensureCore(coreId);
    this.stopPolling();
    const cpu = this.cpuName();
    await this.command('pause');
    await this.setCpuHalted(false, false);
    await this.command(`${cpu} ExecutionMode SingleStepBlocking`);
    await this.command(`${cpu} Step`);
    await this.command(`${cpu} ExecutionMode Continuous`);
    await this.setCpuHalted(true, false);
    this.emit({ event: 'stopped', coreId, reason: 'step' });
  }

  public async reset(coreId: number): Promise<void> {
    this.ensureCore(coreId);
    this.stopPolling();
    await this.command('pause');
    await this.command(this.config?.renodeResetCommand ?? 'machine Reset');
    await this.setCpuHalted(true, false);
    this.emit({ event: 'stopped', coreId, reason: 'restart' });
  }

  public async stack(coreId: number): Promise<StackFrameInfo[]> {
    this.ensureCore(coreId);
    const pc = await this.readRegisterValue('PC');
    let name = '<Renode C2000 instruction frame>';
    try {
      const symbol = await this.command(`${this.sysbusName()} FindSymbolAt 0x${pc.toString(16)}`);
      const lastLine = symbol.split('\n').map((line) => line.trim()).filter(Boolean).pop();
      if (lastLine && !/not found|error/i.test(lastLine)) {
        name = lastLine;
      }
    } catch {
      // Symbol lookup is optional; raw instruction frames still work.
    }
    return [{ id: 1001, name, pc }];
  }

  public async registers(coreId: number): Promise<RegisterValue[]> {
    this.ensureCore(coreId);
    const values: RegisterValue[] = [];
    for (const register of RENODE_C2000_REGISTERS) {
      values.push({
        name: register.name,
        value: await this.readRegisterValue(register.name),
        bits: register.bits,
        group: register.group,
      });
    }
    return values;
  }

  public async writeRegister(coreId: number, name: string, value: bigint): Promise<void> {
    this.ensureCore(coreId);
    const register = RENODE_C2000_REGISTERS.find((item) => item.name === name.toUpperCase());
    if (!register) {
      throw new Error(`Renode C2000 register is not exposed: ${name}`);
    }
    await this.command(`${this.cpuName()} SetRegister ${register.index} 0x${value.toString(16)}`);
  }

  public async evaluate(coreId: number, expression: string): Promise<string> {
    this.ensureCore(coreId);
    const normalized = expression.trim().toUpperCase();
    if (RENODE_C2000_REGISTERS.some((register) => register.name === normalized)) {
      return `0x${(await this.readRegisterValue(normalized)).toString(16)}`;
    }
    if (/^0X[0-9A-F]+$/.test(normalized) || /^\d+$/.test(normalized)) {
      return expression;
    }
    throw new Error('Renode backend evaluation currently supports C2000 register names and integer literals');
  }

  public async readMemory(coreId: number, byteAddress: bigint, byteCount: number): Promise<Buffer> {
    this.ensureCore(coreId);
    if (byteCount < 0) {
      throw new Error('byteCount must be non-negative');
    }
    const range = this.translator.coveringTargetRange(byteAddress, byteCount);
    const words: bigint[] = [];
    for (let index = 0; index < range.targetCount; index += 1) {
      const address = range.firstTarget + BigInt(index);
      words.push(await this.readTargetWord(address));
    }
    const covered = this.translator.wordsToBytes(words, 16);
    return covered.subarray(range.leadingBytes, range.leadingBytes + byteCount);
  }

  public async writeMemory(coreId: number, byteAddress: bigint, data: Buffer): Promise<number> {
    this.ensureCore(coreId);
    if (!data.length) {
      return 0;
    }
    const range = this.translator.coveringTargetRange(byteAddress, data.length);
    const existing: bigint[] = [];
    for (let index = 0; index < range.targetCount; index += 1) {
      existing.push(await this.readTargetWord(range.firstTarget + BigInt(index)));
    }
    const covered = this.translator.wordsToBytes(existing, 16);
    data.copy(covered, range.leadingBytes);
    const words = this.translator.bytesToWords(covered, 16);
    for (let index = 0; index < words.length; index += 1) {
      await this.command(
        `${this.sysbusName()} WriteWord 0x${(range.firstTarget + BigInt(index)).toString(16)} 0x${words[index].toString(16)}`,
      );
    }
    return data.length;
  }

  public async setBreakpoints(coreId: number, breakpoints: BreakpointRequest[]): Promise<BreakpointResult[]> {
    this.ensureCore(coreId);
    const cpu = this.cpuName();
    for (const address of this.breakpointAddresses) {
      try {
        await this.command(`${cpu} RemoveHooksAt 0x${address.toString(16)}`);
      } catch {
        // Older builds may not have the hook or may already have removed it.
      }
    }
    this.breakpointAddresses = [];

    const results: BreakpointResult[] = [];
    for (let index = 0; index < breakpoints.length; index += 1) {
      const breakpoint = breakpoints[index];
      if (breakpoint.address === undefined) {
        results.push({
          id: index + 1,
          verified: false,
          line: breakpoint.line,
          message: 'Renode monitor backend currently requires instruction-address breakpoints',
        });
        continue;
      }
      const address = breakpoint.address;
      const hook = 'self.IsHalted = True; machine.Pause()';
      await this.command(`${cpu} AddHook 0x${address.toString(16)} ${this.stringLiteral(hook)}`);
      this.breakpointAddresses.push(address);
      results.push({ id: index + 1, verified: true, line: breakpoint.line });
    }
    return results;
  }

  public onEvent(listener: (event: BackendEvent) => void): void {
    this.listeners.push(listener);
  }

  private spawnRenode(executable: string, port: number, extraArgs: string[]): void {
    const args = ['--disable-gui', '-P', String(port), ...extraArgs];
    this.process = childProcess.spawn(executable, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    const forward = (chunk: Buffer) => this.emit({ event: 'output', text: chunk.toString() });
    this.process.stdout?.on('data', forward);
    this.process.stderr?.on('data', forward);
    this.process.on('exit', (code: number | null, signal: string | null) => {
      if (!this.stopping) {
        this.emit({
          event: 'output',
          text: `Renode exited unexpectedly (code=${code}, signal=${signal})\n`,
        });
        this.emit({ event: 'terminated' });
      }
    });
  }

  private async connectWithRetry(host: string, port: number, timeoutMs: number): Promise<void> {
    const deadline = Date.now() + timeoutMs;
    let lastError: Error | undefined;
    while (Date.now() < deadline) {
      this.monitor = new RenodeMonitorClient();
      try {
        await this.monitor.connect(host, port, Math.min(1000, Math.max(100, deadline - Date.now())));
        return;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }
    throw new Error(`unable to connect to Renode monitor at ${host}:${port}: ${lastError?.message ?? 'timeout'}`);
  }

  private async loadExecutable(executable: string): Promise<void> {
    const extension = path.extname(executable).toLowerCase();
    const literal = this.pathLiteral(executable);
    if (extension === '.bin') {
      const address = this.parseConfigInteger(this.config?.renodeBinaryLoadAddress ?? 0);
      await this.command(`${this.sysbusName()} LoadBinary @${literal} 0x${address.toString(16)}`, 30000);
      return;
    }
    await this.command(`${this.sysbusName()} LoadELF @${literal}`, 30000);
  }

  private async readRegisterValue(name: string): Promise<bigint> {
    const output = await this.command(`${this.cpuName()} GetRegister ${name}`);
    return this.parseLastInteger(output, `register ${name}`);
  }

  private async readTargetWord(targetAddress: bigint): Promise<bigint> {
    const output = await this.command(`${this.sysbusName()} ReadWord 0x${targetAddress.toString(16)}`);
    return this.parseLastInteger(output, `memory word at 0x${targetAddress.toString(16)}`) & 0xffffn;
  }

  private async setCpuHalted(value: boolean, strict: boolean): Promise<void> {
    try {
      await this.command(`${this.cpuName()} IsHalted ${value ? 'true' : 'false'}`);
    } catch (error) {
      if (strict) throw error;
    }
  }

  private startPolling(coreId: number): void {
    this.stopPolling();
    const pollMs = this.config?.renodeStopPollIntervalMs ?? 100;
    const poll = async () => {
      try {
        const output = await this.command(`${this.cpuName()} IsHalted`, Math.max(1000, pollMs * 5));
        if (/\btrue\b/i.test(output)) {
          this.stopPolling();
          this.emit({ event: 'stopped', coreId, reason: this.breakpointAddresses.length ? 'breakpoint' : 'pause' });
        }
      } catch (error) {
        this.stopPolling();
        this.emit({ event: 'output', text: `Renode stop-state polling failed: ${String(error)}\n` });
      }
    };
    this.stopPoll = setInterval(() => void poll(), pollMs);
  }

  private stopPolling(): void {
    if (this.stopPoll) {
      clearInterval(this.stopPoll);
      this.stopPoll = undefined;
    }
  }

  private parseLastInteger(output: string, label: string): bigint {
    const matches = [...output.matchAll(/(?:0x[0-9a-f]+|\b\d+\b)/gi)];
    const value = matches.pop()?.[0];
    if (!value) {
      throw new Error(`unable to parse ${label} from Renode response: ${output}`);
    }
    return BigInt(value);
  }

  private parseConfigInteger(value: string | number | bigint): bigint {
    if (typeof value === 'bigint') return value;
    if (typeof value === 'number') return BigInt(value);
    const text = String(value).trim();
    if (!/^(?:0x[0-9a-f]+|\d+)$/i.test(text)) {
      throw new Error(`invalid Renode integer: ${value}`);
    }
    return BigInt(text);
  }

  private pathLiteral(value: string): string {
    return this.stringLiteral(path.resolve(value).replace(/\\/g, '/'));
  }

  private stringLiteral(value: string): string {
    return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
  }

  private cpuName(): string {
    return this.config?.renodeCpu ?? 'cpu';
  }

  private sysbusName(): string {
    return this.config?.renodeSysbus ?? 'sysbus';
  }

  private command(command: string, timeoutMs?: number): Promise<string> {
    if (this.config?.trace) {
      this.emit({ event: 'output', text: `[renode] ${command}\n` });
    }
    return this.monitor.command(command, timeoutMs);
  }

  private ensureCore(coreId: number): void {
    if (coreId !== 1 || !this.activeCores.length) {
      throw new Error(`Renode backend exposes one C2000 core, requested ${coreId}`);
    }
  }

  private emit(event: BackendEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
