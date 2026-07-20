"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackendClient = void 0;
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
const readline = __importStar(require("readline"));
const vscode = __importStar(require("vscode"));
const utils_1 = require("./utils");
class BackendClient {
    constructor(context) {
        this.context = context;
        this.pending = new Map();
        this.nextId = 1;
        this.recentErrors = [];
        this.output = vscode.window.createOutputChannel('Open Microchip Tools');
    }
    async request(command, args = {}, options) {
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
            proc.stdin.write(payload + '\n', 'utf8', (err) => {
                if (err) {
                    this.pending.delete(id);
                    reject(err);
                }
            });
        }).catch((error) => {
            if (options?.recordError !== false) {
                this.recordError(error instanceof Error ? error.message : String(error));
            }
            throw error;
        });
    }
    show() {
        this.output.show(true);
    }
    log(value) {
        this.output.appendLine((0, utils_1.stringify)(value));
    }
    getRecentErrors(limit = 5) {
        return this.recentErrors.slice(0, Math.max(0, limit));
    }
    clearRecentErrors() {
        this.recentErrors.length = 0;
    }
    dispose() {
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
    async ensureStarted() {
        if (this.process) {
            return;
        }
        const config = vscode.workspace.getConfiguration('openMicrochipTools');
        const pythonPath = config.get('pythonPath', 'python');
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
        this.process.stderr.on('data', (chunk) => {
            this.output.append(chunk.toString());
        });
        this.process.on('exit', (code, signal) => {
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
        rl.on('line', (line) => {
            let response;
            try {
                response = JSON.parse(line);
            }
            catch {
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
            }
            else {
                pending.reject(new Error(response.error ?? 'Unknown backend error'));
            }
        });
        await this.request('ping');
    }
    recordError(message) {
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
exports.BackendClient = BackendClient;
//# sourceMappingURL=backendClient.js.map