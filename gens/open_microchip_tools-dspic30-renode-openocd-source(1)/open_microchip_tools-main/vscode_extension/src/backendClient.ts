import * as cp from 'child_process';
import * as path from 'path';
import * as readline from 'readline';
import * as vscode from 'vscode';

import { type BackendResponse } from './types';
import { stringify } from './utils';

export class BackendClient implements vscode.Disposable {
  private readonly output: vscode.OutputChannel;
  private process: cp.ChildProcessWithoutNullStreams | undefined;
  private pending = new Map<number, { resolve: (value: unknown) => void; reject: (reason?: unknown) => void }>();
  private nextId = 1;
  private readonly recentErrors: string[] = [];

  constructor(private readonly context: vscode.ExtensionContext) {
    this.output = vscode.window.createOutputChannel('Open Microchip Tools');
  }

  async request(command: string, args: Record<string, unknown> = {}, options?: { recordError?: boolean }): Promise<unknown> {
    await this.ensureStarted();
    const proc = this.process;
    if (!proc) {
      const error = new Error('Backend process is not running');
      if (options?.recordError !== false) {
        this.recordError(error.message);
      }
      throw error;
    }

    const id = this.nextId++;
    const payload = JSON.stringify({ id, command, args });

    return await new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      proc.stdin.write(payload + '\n', 'utf8', (err?: Error | null) => {
        if (err) {
          this.pending.delete(id);
          reject(err);
        }
      });
    }).catch((error: unknown) => {
      if (options?.recordError !== false) {
        this.recordError(error instanceof Error ? error.message : String(error));
      }
      throw error;
    });
  }

  show(): void {
    this.output.show(true);
  }

  log(value: unknown): void {
    this.output.appendLine(stringify(value));
  }

  getRecentErrors(limit = 5): string[] {
    return this.recentErrors.slice(0, Math.max(0, limit));
  }

  clearRecentErrors(): void {
    this.recentErrors.length = 0;
  }

  dispose(): void {
    for (const pending of this.pending.values()) {
      pending.reject(new Error('Backend disposed'));
    }
    this.pending.clear();
    if (this.process) {
      this.process.kill();
      this.process = undefined;
    }
    this.output.dispose();
  }

  private async ensureStarted(): Promise<void> {
    if (this.process) {
      return;
    }

    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    const pythonPath = config.get<string>('pythonPath', 'python');
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const cwd = workspaceFolder?.uri.fsPath ?? this.context.extensionPath;
    const repoRoot = workspaceFolder?.uri.fsPath ?? path.resolve(this.context.extensionPath, '..');

    const env = {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${repoRoot}${path.delimiter}${process.env.PYTHONPATH}` : repoRoot,
    };

    this.process = cp.spawn(pythonPath, ['-u', '-m', 'mchp_vscode.backend_server'], {
      cwd,
      env,
      stdio: 'pipe',
    });

    this.process.stderr.on('data', (chunk: Buffer | string) => {
      this.output.append(chunk.toString());
    });
    this.process.on('exit', (code: number | null, signal: NodeJS.Signals | null) => {
      const msg = `Backend exited code=${code ?? 'null'} signal=${signal ?? 'null'}`;
      this.recordError(msg);
      this.output.appendLine(msg);
      for (const pending of this.pending.values()) {
        pending.reject(new Error(msg));
      }
      this.pending.clear();
      this.process = undefined;
    });

    const rl = readline.createInterface({ input: this.process.stdout });
    rl.on('line', (line: string) => {
      let response: BackendResponse & { id?: number };
      try {
        response = JSON.parse(line);
      } catch {
        this.recordError(`Invalid backend JSON: ${line}`);
        this.output.appendLine(`Invalid backend JSON: ${line}`);
        return;
      }
      const pending = this.pending.get(Number(response.id));
      if (!pending) {
        return;
      }
      this.pending.delete(Number(response.id));
      if (response.ok) {
        pending.resolve(response.result);
      } else {
        pending.reject(new Error(response.error ?? 'Unknown backend error'));
      }
    });

    await this.request('ping');
  }

  private recordError(message: string): void {
    const text = message.trim();
    if (!text) {
      return;
    }
    this.recentErrors.unshift(text);
    if (this.recentErrors.length > 10) {
      this.recentErrors.length = 10;
    }
  }
}