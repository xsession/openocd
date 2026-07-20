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
import { BridgeClient } from './bridgeClient';

export class CcsBackend implements Backend {
  private readonly bridge = new BridgeClient();
  private readonly listeners: Array<(event: BackendEvent) => void> = [];
  private activeCores: DebugCore[] = [];

  public constructor() {
    this.bridge.onEvent((event) => this.emit(event));
    this.bridge.onOutput((text) => this.emit({ event: 'output', text }));
  }

  public async start(config: LaunchConfig): Promise<DebugCore[]> {
    if (!config.ccxml) {
      throw new Error('ccxml is required for the CCS backend');
    }
    await this.bridge.start(config);
    const result = await this.bridge.request('threads');
    const bridgeCores = result.cores ?? result;
    this.activeCores = bridgeCores.map((core: any) => ({
      id: Number(core.id),
      name: String(core.name),
      architecture: core.architecture,
      device: core.device ?? config.device,
      addressScale: Number(core.addressScale ?? (core.architecture === 'c28x' ? 2 : 1)),
    }));
    const haltedCoreIds = bridgeCores
      .filter((core: any) => Boolean(core.halted))
      .map((core: any) => Number(core.id));
    setTimeout(() => {
      for (const coreId of haltedCoreIds) {
        this.emit({ event: 'stopped', coreId, reason: 'entry' });
      }
    }, 0);
    return this.activeCores;
  }

  public async stop(terminate: boolean): Promise<void> {
    try {
      await this.bridge.request('disconnect', { terminate }, 10000);
    } finally {
      await this.bridge.stop();
    }
  }

  public cores(): DebugCore[] {
    return this.activeCores;
  }

  public async continue(coreId: number): Promise<void> {
    await this.bridge.request('continue', { coreId });
  }

  public async halt(coreId: number): Promise<void> {
    await this.bridge.request('halt', { coreId });
  }

  public async step(coreId: number, kind: 'into' | 'over' | 'out' | 'instruction'): Promise<void> {
    await this.bridge.request('step', { coreId, kind });
  }

  public async reset(coreId: number): Promise<void> {
    await this.bridge.request('reset', { coreId });
  }

  public async stack(coreId: number): Promise<StackFrameInfo[]> {
    const result = await this.bridge.request('stack', { coreId });
    return (result.frames ?? result).map((frame: any, index: number) => ({
      id: Number(frame.id ?? coreId * 1000 + index + 1),
      name: String(frame.name ?? '<unknown>'),
      pc: BigInt(frame.pc),
      source: frame.source,
      line: frame.line,
      column: frame.column,
    }));
  }

  public async registers(coreId: number): Promise<RegisterValue[]> {
    const result = await this.bridge.request('registers', { coreId });
    return (result.registers ?? result).map((register: any) => ({
      name: String(register.name),
      value: BigInt(register.value),
      bits: Number(register.bits ?? 32),
      group: register.group,
    }));
  }

  public async writeRegister(coreId: number, name: string, value: bigint): Promise<void> {
    await this.bridge.request('writeRegister', { coreId, name, value: value.toString() });
  }

  public async evaluate(coreId: number, expression: string): Promise<string> {
    const result = await this.bridge.request('evaluate', { coreId, expression });
    return String(result.value ?? result);
  }

  public async readMemory(coreId: number, byteAddress: bigint, byteCount: number): Promise<Buffer> {
    const result = await this.bridge.request('readMemory', {
      coreId,
      byteAddress: byteAddress.toString(),
      byteCount,
    });
    return Buffer.from(result.data, 'base64');
  }

  public async writeMemory(coreId: number, byteAddress: bigint, data: Buffer): Promise<number> {
    const result = await this.bridge.request('writeMemory', {
      coreId,
      byteAddress: byteAddress.toString(),
      data: data.toString('base64'),
    });
    return Number(result.bytesWritten ?? data.length);
  }

  public async setBreakpoints(coreId: number, breakpoints: BreakpointRequest[]): Promise<BreakpointResult[]> {
    const result = await this.bridge.request('setBreakpoints', {
      coreId,
      breakpoints: breakpoints.map((breakpoint) => ({
        ...breakpoint,
        address: breakpoint.address?.toString(),
      })),
    });
    return result.breakpoints ?? result;
  }

  public onEvent(listener: (event: BackendEvent) => void): void {
    this.listeners.push(listener);
  }

  private emit(event: BackendEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
