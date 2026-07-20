import path = require('node:path');
import { DapRequest, DapTransport } from './dap';
import { Backend, BackendEvent, BreakpointRequest, DebugCore, LaunchConfig, RegisterValue } from './protocol';
import { CcsBackend } from './backends/ccsBackend';
import { MockBackend } from './backends/mockBackend';
import { OpenOcdBackend } from './backends/openocdBackend';

class C2000DebugAdapter {
  private readonly transport = new DapTransport();
  private backend?: Backend;
  private cores: DebugCore[] = [];
  private launchConfig?: LaunchConfig;
  private readonly frameToCore = new Map<number, number>();
  private readonly registerCache = new Map<number, RegisterValue[]>();
  private configured = false;

  public constructor() {
    this.transport.onRequest((request) => {
      void this.dispatch(request);
    });
  }

  private async dispatch(request: DapRequest): Promise<void> {
    try {
      switch (request.command) {
        case 'initialize':
          this.initialize(request);
          break;
        case 'launch':
        case 'attach':
          await this.launch(request);
          break;
        case 'configurationDone':
          this.configured = true;
          this.transport.response(request);
          break;
        case 'threads':
          this.transport.response(request, {
            threads: this.cores.map((core) => ({ id: core.id, name: core.name })),
          });
          break;
        case 'stackTrace':
          await this.stackTrace(request);
          break;
        case 'scopes':
          this.scopes(request);
          break;
        case 'variables':
          await this.variables(request);
          break;
        case 'setVariable':
          await this.setVariable(request);
          break;
        case 'evaluate':
          await this.evaluate(request);
          break;
        case 'setBreakpoints':
          await this.setBreakpoints(request);
          break;
        case 'setInstructionBreakpoints':
          await this.setInstructionBreakpoints(request);
          break;
        case 'continue':
          await this.coreCommand(request, (backend, coreId) => backend.continue(coreId), { allThreadsContinued: false });
          break;
        case 'pause':
          await this.coreCommand(request, (backend, coreId) => backend.halt(coreId));
          break;
        case 'next':
          await this.coreCommand(request, (backend, coreId) => backend.step(coreId, 'over'));
          break;
        case 'stepIn':
          await this.coreCommand(request, (backend, coreId) => backend.step(coreId, 'into'));
          break;
        case 'stepOut':
          await this.coreCommand(request, (backend, coreId) => backend.step(coreId, 'out'));
          break;
        case 'restart':
          await this.restart(request);
          break;
        case 'readMemory':
          await this.readMemory(request);
          break;
        case 'writeMemory':
          await this.writeMemory(request);
          break;
        case 'disconnect':
        case 'terminate':
          await this.disconnect(request);
          break;
        case 'modules':
          this.transport.response(request, { modules: [], totalModules: 0 });
          break;
        case 'loadedSources':
          this.transport.response(request, { sources: [] });
          break;
        case 'exceptionInfo':
          this.transport.response(request, {
            exceptionId: 'C2000 halt',
            breakMode: 'always',
            description: 'The target is halted by the debugger.',
          });
          break;
        default:
          this.transport.error(request, new Error(`unsupported DAP request: ${request.command}`));
      }
    } catch (error) {
      this.transport.error(request, error);
    }
  }

  private initialize(request: DapRequest): void {
    this.transport.response(request, {
      supportsConfigurationDoneRequest: true,
      supportsEvaluateForHovers: true,
      supportsSetVariable: true,
      supportsRestartRequest: true,
      supportsReadMemoryRequest: true,
      supportsWriteMemoryRequest: true,
      supportsInstructionBreakpoints: true,
      supportsTerminateRequest: true,
      supportsLoadedSourcesRequest: true,
      supportsModulesRequest: true,
      supportsExceptionInfoRequest: true,
      supportTerminateDebuggee: true,
      supportSuspendDebuggee: true,
    });
    this.transport.event('initialized');
  }

  private async launch(request: DapRequest): Promise<void> {
    const config = this.normalizeConfig(request.arguments ?? {}, request.command as 'launch' | 'attach');
    this.launchConfig = config;
    this.backend = this.createBackend(config.backend);
    this.backend.onEvent((event) => this.backendEvent(event));
    this.cores = await this.backend.start(config);
    if (!this.cores.length) {
      throw new Error('backend returned no debuggable cores');
    }
    this.transport.response(request);
    this.transport.event('process', {
      name: `${config.device} via ${config.backend}`,
      systemProcessId: 0,
      isLocalProcess: true,
      startMethod: request.command,
    });
    this.transport.event('thread', { reason: 'started', threadId: this.cores[0].id });
    for (const core of this.cores.slice(1)) {
      this.transport.event('thread', { reason: 'started', threadId: core.id });
    }
  }

  private normalizeConfig(input: any, request: 'launch' | 'attach'): LaunchConfig {
    if (!input.backend || !input.device) {
      throw new Error('backend and device are required');
    }
    const substitute = (value: string | undefined): string | undefined => {
      if (!value) {
        return value;
      }
      return value.replace(/\$\{workspaceFolder\}/g, process.cwd());
    };
    return {
      ...input,
      request,
      executable: substitute(input.executable),
      ccsRoot: substitute(input.ccsRoot),
      ccxml: substitute(input.ccxml),
      svdPath: substitute(input.svdPath),
      bridgeScript: substitute(input.bridgeScript),
      addressScale: input.addressScale ?? (String(input.device).endsWith('_m3') ? 1 : 2),
      cores: input.cores?.map((core: any) => ({
        ...core,
        executable: substitute(core.executable),
      })),
    };
  }

  private createBackend(kind: string): Backend {
    switch (kind) {
      case 'ccs':
        return new CcsBackend();
      case 'openocd':
        return new OpenOcdBackend();
      case 'mock':
        return new MockBackend();
      default:
        throw new Error(`unknown backend: ${kind}`);
    }
  }

  private async stackTrace(request: DapRequest): Promise<void> {
    const backend = this.requireBackend();
    const coreId = this.coreId(request.arguments?.threadId);
    const frames = await backend.stack(coreId);
    for (const frame of frames) {
      this.frameToCore.set(frame.id, coreId);
    }
    this.transport.response(request, {
      stackFrames: frames.map((frame) => ({
        id: frame.id,
        name: frame.name,
        instructionPointerReference: `0x${frame.pc.toString(16)}`,
        source: frame.source ? { name: path.basename(frame.source), path: frame.source } : undefined,
        line: frame.line ?? 1,
        column: frame.column ?? 1,
      })),
      totalFrames: frames.length,
    });
  }

  private scopes(request: DapRequest): void {
    const frameId = Number(request.arguments?.frameId);
    const coreId = this.frameToCore.get(frameId) ?? this.cores[0]?.id ?? 1;
    this.transport.response(request, {
      scopes: [
        {
          name: 'CPU Registers',
          presentationHint: 'registers',
          variablesReference: this.registerReference(coreId),
          expensive: false,
        },
        {
          name: 'Expressions',
          variablesReference: 0,
          expensive: false,
        },
      ],
    });
  }

  private async variables(request: DapRequest): Promise<void> {
    const reference = Number(request.arguments?.variablesReference);
    const coreId = this.coreFromRegisterReference(reference);
    if (coreId === undefined) {
      this.transport.response(request, { variables: [] });
      return;
    }
    const registers = await this.requireBackend().registers(coreId);
    this.registerCache.set(coreId, registers);
    this.transport.response(request, {
      variables: registers.map((register) => ({
        name: register.name,
        value: this.formatRegister(register),
        type: `${register.bits}-bit register${register.group ? ` / ${register.group}` : ''}`,
        variablesReference: 0,
        evaluateName: register.name,
        memoryReference: register.name.toUpperCase() === 'PC' ? `0x${register.value.toString(16)}` : undefined,
      })),
    });
  }

  private async setVariable(request: DapRequest): Promise<void> {
    const reference = Number(request.arguments?.variablesReference);
    const coreId = this.coreFromRegisterReference(reference);
    if (coreId === undefined) {
      throw new Error('setVariable is only supported for the CPU Registers scope');
    }
    const name = String(request.arguments?.name ?? '');
    const value = this.parseInteger(String(request.arguments?.value ?? ''));
    await this.requireBackend().writeRegister(coreId, name, value);
    this.transport.response(request, { value: `0x${value.toString(16)}`, type: 'register' });
  }

  private async evaluate(request: DapRequest): Promise<void> {
    const frameId = Number(request.arguments?.frameId ?? 0);
    const coreId = this.frameToCore.get(frameId) ?? this.cores[0]?.id ?? 1;
    const expression = String(request.arguments?.expression ?? '');
    const value = await this.requireBackend().evaluate(coreId, expression);
    this.transport.response(request, { result: value, variablesReference: 0 });
  }

  private async setBreakpoints(request: DapRequest): Promise<void> {
    const backend = this.requireBackend();
    const coreId = this.cores[0]?.id ?? 1;
    const source = request.arguments?.source?.path;
    const breakpoints: BreakpointRequest[] = (request.arguments?.breakpoints ?? []).map((breakpoint: any) => ({
      source,
      line: Number(breakpoint.line),
    }));
    const result = await backend.setBreakpoints(coreId, breakpoints);
    this.transport.response(request, {
      breakpoints: result.map((breakpoint) => ({
        id: breakpoint.id,
        verified: breakpoint.verified,
        line: breakpoint.line,
        message: breakpoint.message,
      })),
    });
  }

  private async setInstructionBreakpoints(request: DapRequest): Promise<void> {
    const backend = this.requireBackend();
    const coreId = this.cores[0]?.id ?? 1;
    const breakpoints: BreakpointRequest[] = (request.arguments?.breakpoints ?? []).map((breakpoint: any) => ({
      address: this.parseInteger(String(breakpoint.instructionReference)) + BigInt(breakpoint.offset ?? 0),
    }));
    const result = await backend.setBreakpoints(coreId, breakpoints);
    this.transport.response(request, {
      breakpoints: result.map((breakpoint) => ({
        id: breakpoint.id,
        verified: breakpoint.verified,
        instructionReference: breakpoints.find((_, index) => result[index] === breakpoint)?.address?.toString(),
        message: breakpoint.message,
      })),
    });
  }

  private async coreCommand(
    request: DapRequest,
    action: (backend: Backend, coreId: number) => Promise<void>,
    body?: any,
  ): Promise<void> {
    const coreId = this.coreId(request.arguments?.threadId);
    await action(this.requireBackend(), coreId);
    this.transport.response(request, body);
  }

  private async restart(request: DapRequest): Promise<void> {
    const backend = this.requireBackend();
    for (const core of this.cores) {
      await backend.reset(core.id);
    }
    this.transport.response(request);
  }

  private async readMemory(request: DapRequest): Promise<void> {
    const coreId = this.coreId(request.arguments?.threadId ?? this.cores[0]?.id);
    const base = this.parseInteger(String(request.arguments?.memoryReference ?? '0'));
    const address = base + BigInt(request.arguments?.offset ?? 0);
    const count = Number(request.arguments?.count ?? 0);
    const data = await this.requireBackend().readMemory(coreId, address, count);
    this.transport.response(request, {
      address: `0x${address.toString(16)}`,
      data: data.toString('base64'),
      unreadableBytes: Math.max(0, count - data.length),
    });
  }

  private async writeMemory(request: DapRequest): Promise<void> {
    const coreId = this.coreId(request.arguments?.threadId ?? this.cores[0]?.id);
    const base = this.parseInteger(String(request.arguments?.memoryReference ?? '0'));
    const address = base + BigInt(request.arguments?.offset ?? 0);
    const data = Buffer.from(String(request.arguments?.data ?? ''), 'base64');
    const bytesWritten = await this.requireBackend().writeMemory(coreId, address, data);
    this.transport.response(request, { bytesWritten, offset: 0 });
  }

  private async disconnect(request: DapRequest): Promise<void> {
    if (this.backend) {
      await this.backend.stop(Boolean(request.arguments?.terminateDebuggee));
    }
    this.transport.response(request);
    this.transport.event('terminated');
    setTimeout(() => process.exit(0), 10);
  }

  private backendEvent(event: BackendEvent): void {
    switch (event.event) {
      case 'stopped':
        this.registerCache.delete(event.coreId ?? 1);
        this.transport.event('stopped', {
          reason: event.reason ?? 'pause',
          threadId: event.coreId ?? 1,
          allThreadsStopped: false,
        });
        break;
      case 'continued':
        this.transport.event('continued', {
          threadId: event.coreId ?? 1,
          allThreadsContinued: false,
        });
        break;
      case 'output':
        this.transport.event('output', { category: 'console', output: event.text ?? '' });
        break;
      case 'terminated':
        this.transport.event('terminated', { restart: false });
        break;
    }
  }

  private coreId(value: unknown): number {
    const id = Number(value ?? this.cores[0]?.id ?? 1);
    if (!this.cores.some((core) => core.id === id)) {
      throw new Error(`unknown thread/core ${id}`);
    }
    return id;
  }

  private registerReference(coreId: number): number {
    return 100000 + coreId;
  }

  private coreFromRegisterReference(reference: number): number | undefined {
    const coreId = reference - 100000;
    return this.cores.some((core) => core.id === coreId) ? coreId : undefined;
  }

  private formatRegister(register: RegisterValue): string {
    const nibbles = Math.max(1, Math.ceil(register.bits / 4));
    return `0x${register.value.toString(16).padStart(nibbles, '0')}`;
  }

  private parseInteger(text: string): bigint {
    const normalized = text.trim();
    if (/^[+-]?0x[0-9a-f]+$/i.test(normalized) || /^[+-]?\d+$/.test(normalized)) {
      return BigInt(normalized);
    }
    throw new Error(`invalid integer: ${text}`);
  }

  private requireBackend(): Backend {
    if (!this.backend) {
      throw new Error('debug backend has not been launched');
    }
    return this.backend;
  }
}

new C2000DebugAdapter();
