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

interface MockCoreState {
  core: DebugCore;
  registers: Map<string, bigint>;
  memory: Buffer;
  breakpoints: BreakpointResult[];
  halted: boolean;
}

export class MockBackend implements Backend {
  private readonly listeners: Array<(event: BackendEvent) => void> = [];
  private readonly states = new Map<number, MockCoreState>();
  private launchConfig?: LaunchConfig;

  public async start(config: LaunchConfig): Promise<DebugCore[]> {
    this.launchConfig = config;
    const definitions = config.cores?.length
      ? config.cores
      : [{
          name: config.device,
          pattern: config.corePattern ?? 'C28xx',
          architecture: config.device.endsWith('_m3') ? 'cortex-m3' as const : 'c28x' as const,
          device: config.device,
          addressScale: config.addressScale,
        }];
    const cores: DebugCore[] = definitions.map((definition, index) => ({
      id: index + 1,
      name: definition.name,
      architecture: definition.architecture,
      device: definition.device ?? config.device,
      addressScale: definition.addressScale ?? (definition.architecture === 'c28x' ? 2 : 1),
    }));

    for (const core of cores) {
      const registers = new Map<string, bigint>();
      for (const definition of profileFor(core.device, core.architecture, config.registerProfile)) {
        registers.set(definition.name, 0n);
      }
      registers.set('PC', 0x8000n + BigInt(core.id * 0x100));
      registers.set('SP', 0x400n + BigInt(core.id * 0x20));
      const memory = Buffer.alloc(1024 * 1024);
      for (let index = 0; index < memory.length; index += 1) {
        memory[index] = index & 0xff;
      }
      this.states.set(core.id, { core, registers, memory, breakpoints: [], halted: true });
    }
    queueMicrotask(() => this.emit({ event: 'stopped', coreId: 1, reason: 'entry' }));
    return cores;
  }

  public async stop(_terminate: boolean): Promise<void> {
    this.states.clear();
  }

  public cores(): DebugCore[] {
    return [...this.states.values()].map((state) => state.core);
  }

  public async continue(coreId: number): Promise<void> {
    const state = this.state(coreId);
    state.halted = false;
    this.emit({ event: 'continued', coreId });
    setTimeout(() => {
      const current = this.states.get(coreId);
      if (!current || current.halted) {
        return;
      }
      current.halted = true;
      current.registers.set('PC', (current.registers.get('PC') ?? 0n) + 2n);
      this.emit({ event: 'stopped', coreId, reason: current.breakpoints.length ? 'breakpoint' : 'pause' });
    }, 25);
  }

  public async halt(coreId: number): Promise<void> {
    this.state(coreId).halted = true;
    this.emit({ event: 'stopped', coreId, reason: 'pause' });
  }

  public async step(coreId: number, _kind: 'into' | 'over' | 'out' | 'instruction'): Promise<void> {
    const state = this.state(coreId);
    state.registers.set('PC', (state.registers.get('PC') ?? 0n) + 1n);
    this.emit({ event: 'stopped', coreId, reason: 'step' });
  }

  public async reset(coreId: number): Promise<void> {
    const state = this.state(coreId);
    state.registers.set('PC', 0n);
    state.halted = true;
    this.emit({ event: 'stopped', coreId, reason: 'restart' });
  }

  public async stack(coreId: number): Promise<StackFrameInfo[]> {
    const pc = this.state(coreId).registers.get('PC') ?? 0n;
    return [{
      id: coreId * 1000 + 1,
      name: `mock_function_${coreId}`,
      pc,
      source: this.launchConfig?.executable ? `${this.launchConfig.executable}.c` : undefined,
      line: 1,
      column: 1,
    }];
  }

  public async registers(coreId: number): Promise<RegisterValue[]> {
    const state = this.state(coreId);
    const definitions = profileFor(state.core.device, state.core.architecture, this.launchConfig?.registerProfile);
    return definitions.map((definition) => ({
      name: definition.name,
      value: state.registers.get(definition.name) ?? 0n,
      bits: definition.bits,
      group: definition.group,
    }));
  }

  public async writeRegister(coreId: number, name: string, value: bigint): Promise<void> {
    this.state(coreId).registers.set(name, value);
  }

  public async evaluate(coreId: number, expression: string): Promise<string> {
    const state = this.state(coreId);
    const register = state.registers.get(expression.toUpperCase());
    if (register !== undefined) {
      return `0x${register.toString(16)}`;
    }
    if (/^0x[0-9a-f]+$/i.test(expression)) {
      return expression;
    }
    if (/^\d+$/.test(expression)) {
      return expression;
    }
    return `<mock:${expression}>`;
  }

  public async readMemory(coreId: number, byteAddress: bigint, byteCount: number): Promise<Buffer> {
    const state = this.state(coreId);
    const start = Number(byteAddress);
    if (!Number.isSafeInteger(start) || start < 0 || start + byteCount > state.memory.length) {
      throw new Error(`memory read outside mock range: 0x${byteAddress.toString(16)} + ${byteCount}`);
    }
    return Buffer.from(state.memory.subarray(start, start + byteCount));
  }

  public async writeMemory(coreId: number, byteAddress: bigint, data: Buffer): Promise<number> {
    const state = this.state(coreId);
    const start = Number(byteAddress);
    if (!Number.isSafeInteger(start) || start < 0 || start + data.length > state.memory.length) {
      throw new Error(`memory write outside mock range: 0x${byteAddress.toString(16)} + ${data.length}`);
    }
    data.copy(state.memory, start);
    return data.length;
  }

  public async setBreakpoints(coreId: number, breakpoints: BreakpointRequest[]): Promise<BreakpointResult[]> {
    const state = this.state(coreId);
    state.breakpoints = breakpoints.map((breakpoint, index) => ({
      id: coreId * 10000 + index + 1,
      verified: true,
      line: breakpoint.line,
    }));
    return state.breakpoints;
  }

  public onEvent(listener: (event: BackendEvent) => void): void {
    this.listeners.push(listener);
  }

  private state(coreId: number): MockCoreState {
    const state = this.states.get(coreId);
    if (!state) {
      throw new Error(`unknown core/thread ${coreId}`);
    }
    return state;
  }

  private emit(event: BackendEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
