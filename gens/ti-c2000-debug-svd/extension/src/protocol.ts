export type Architecture = 'c28x' | 'cortex-m3';
export type BackendKind = 'ccs' | 'openocd' | 'mock';

export interface CoreLaunchConfig {
  name: string;
  pattern: string;
  architecture: Architecture;
  device?: string;
  executable?: string;
  loadProgram?: boolean;
  addressScale?: number;
}

export interface LaunchConfig {
  backend: BackendKind;
  device: string;
  request?: 'launch' | 'attach';
  executable?: string;
  ccsRoot?: string;
  ccxml?: string;
  corePattern?: string;
  cores?: CoreLaunchConfig[];
  svdPath?: string;
  addressScale?: number;
  runToEntryPoint?: string | null;
  stopOnEntry?: boolean;
  resetOnLaunch?: boolean;
  verifyProgram?: boolean;
  bridgeScript?: string;
  bridgeCommand?: string;
  bridgeArgs?: string[];
  openocdHost?: string;
  openocdTelnetPort?: number;
  registerProfile?: string;
  trace?: boolean;
}

export interface DebugCore {
  id: number;
  name: string;
  architecture: Architecture;
  device: string;
  addressScale: number;
}

export interface RegisterValue {
  name: string;
  value: bigint;
  bits: number;
  group?: string;
}

export interface StackFrameInfo {
  id: number;
  name: string;
  pc: bigint;
  source?: string;
  line?: number;
  column?: number;
}

export interface BreakpointRequest {
  source?: string;
  line?: number;
  expression?: string;
  address?: bigint;
}

export interface BreakpointResult {
  id: number;
  verified: boolean;
  line?: number;
  message?: string;
}

export interface BackendEvent {
  event: 'stopped' | 'continued' | 'output' | 'terminated';
  coreId?: number;
  reason?: string;
  text?: string;
}

export interface Backend {
  start(config: LaunchConfig): Promise<DebugCore[]>;
  stop(terminate: boolean): Promise<void>;
  cores(): DebugCore[];
  continue(coreId: number): Promise<void>;
  halt(coreId: number): Promise<void>;
  step(coreId: number, kind: 'into' | 'over' | 'out' | 'instruction'): Promise<void>;
  reset(coreId: number): Promise<void>;
  stack(coreId: number): Promise<StackFrameInfo[]>;
  registers(coreId: number): Promise<RegisterValue[]>;
  writeRegister(coreId: number, name: string, value: bigint): Promise<void>;
  evaluate(coreId: number, expression: string): Promise<string>;
  readMemory(coreId: number, byteAddress: bigint, byteCount: number): Promise<Buffer>;
  writeMemory(coreId: number, byteAddress: bigint, data: Buffer): Promise<number>;
  setBreakpoints(coreId: number, breakpoints: BreakpointRequest[]): Promise<BreakpointResult[]>;
  onEvent(listener: (event: BackendEvent) => void): void;
}
