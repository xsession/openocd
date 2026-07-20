import childProcess = require('node:child_process');
import path = require('node:path');
import readline = require('node:readline');
import { BackendEvent, LaunchConfig } from '../protocol';

interface PendingRequest {
  resolve: (value: any) => void;
  reject: (error: Error) => void;
  timer: any;
}

export class BridgeClient {
  private child: any;
  private sequence = 1;
  private readonly pending = new Map<number, PendingRequest>();
  private readonly eventListeners: Array<(event: BackendEvent) => void> = [];
  private readonly outputListeners: Array<(text: string) => void> = [];

  public async start(config: LaunchConfig): Promise<void> {
    const bridgeScript = config.bridgeScript ?? path.resolve(__dirname, '..', '..', 'bridge', 'ccs-debug-bridge.js');
    const command = config.bridgeCommand ?? this.defaultRunner(config.ccsRoot);
    const args = config.bridgeCommand
      ? [...(config.bridgeArgs ?? []), bridgeScript]
      : [bridgeScript];

    this.child = childProcess.spawn(command, args, {
      cwd: process.cwd(),
      env: { ...process.env, C2000_CCS_ROOT: config.ccsRoot ?? '' },
      shell: process.platform === 'win32' && command.toLowerCase().endsWith('.bat'),
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    this.child.on('error', (error: Error) => this.failAll(error));
    this.child.on('exit', (code: number, signal: string) => {
      const error = new Error(`CCS bridge exited (${code ?? 'null'}, ${signal ?? 'none'})`);
      this.failAll(error);
      this.emitEvent({ event: 'terminated', reason: error.message });
    });
    this.child.stderr.on('data', (chunk: Buffer) => this.emitOutput(chunk.toString()));

    const lines = readline.createInterface({ input: this.child.stdout });
    lines.on('line', (line: string) => this.handleLine(line));

    await this.request('initialize', {
      ccsRoot: config.ccsRoot,
      ccxml: config.ccxml,
      device: config.device,
      executable: config.executable,
      corePattern: config.corePattern,
      cores: config.cores,
      addressScale: config.addressScale,
      registerProfile: config.registerProfile,
      request: config.request,
      resetOnLaunch: config.resetOnLaunch,
      verifyProgram: config.verifyProgram,
      runToEntryPoint: config.runToEntryPoint,
      stopOnEntry: config.stopOnEntry,
    }, 120000);
  }

  public request(method: string, params: Record<string, unknown> = {}, timeoutMs = 30000): Promise<any> {
    if (!this.child?.stdin?.writable) {
      return Promise.reject(new Error('CCS bridge is not running'));
    }
    const id = this.sequence++;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CCS bridge request timed out: ${method}`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${payload}\n`);
    });
  }

  public async stop(): Promise<void> {
    try {
      await this.request('shutdown', {}, 5000);
    } catch {
      // Process termination below is the final fallback.
    }
    this.child?.kill();
  }

  public onEvent(listener: (event: BackendEvent) => void): void {
    this.eventListeners.push(listener);
  }

  public onOutput(listener: (text: string) => void): void {
    this.outputListeners.push(listener);
  }

  private defaultRunner(ccsRoot?: string): string {
    if (!ccsRoot) {
      throw new Error('ccsRoot is required for the CCS backend unless bridgeCommand is supplied');
    }
    return path.join(ccsRoot, 'ccs', 'scripting', process.platform === 'win32' ? 'run.bat' : 'run.sh');
  }

  private handleLine(line: string): void {
    const marker = '@@C2000@@';
    if (!line.startsWith(marker)) {
      this.emitOutput(`${line}\n`);
      return;
    }
    let message: any;
    try {
      message = JSON.parse(line.slice(marker.length));
    } catch (error) {
      this.emitOutput(`invalid bridge JSON: ${line}\n`);
      return;
    }
    if (typeof message.id === 'number') {
      const pending = this.pending.get(message.id);
      if (!pending) {
        return;
      }
      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.ok) {
        pending.resolve(message.result);
      } else {
        pending.reject(new Error(message.error?.message ?? String(message.error ?? 'bridge request failed')));
      }
      return;
    }
    if (message.event) {
      this.emitEvent(message as BackendEvent);
    }
  }

  private failAll(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  private emitEvent(event: BackendEvent): void {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }

  private emitOutput(text: string): void {
    for (const listener of this.outputListeners) {
      listener(text);
    }
  }
}
