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
exports.persistHardwareSessionDefaults = persistHardwareSessionDefaults;
exports.persistZephyrStubDemoDefaults = persistZephyrStubDemoDefaults;
exports.loadZephyrStubDemoDefaults = loadZephyrStubDemoDefaults;
const vscode = __importStar(require("vscode"));
async function persistHardwareSessionDefaults(options) {
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    await Promise.all([
        config.update('hardwareProcessor', options.processor ?? '', vscode.ConfigurationTarget.Workspace),
        config.update('hardwareScriptsPath', options.scriptsPath ?? '', vscode.ConfigurationTarget.Workspace),
        config.update('hardwareToolScriptsPath', options.toolScriptsPath ?? '', vscode.ConfigurationTarget.Workspace),
    ]);
}
async function persistZephyrStubDemoDefaults(options) {
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    await Promise.all([
        config.update('zephyrStubFamily', options.family, vscode.ConfigurationTarget.Workspace),
        config.update('zephyrStubProcessor', options.processor, vscode.ConfigurationTarget.Workspace),
        config.update('zephyrStubWriteAddress', options.writeAddress, vscode.ConfigurationTarget.Workspace),
        config.update('zephyrStubWriteHex', options.writeHex, vscode.ConfigurationTarget.Workspace),
    ]);
}
function loadZephyrStubDemoDefaults() {
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    return {
        family: config.get('zephyrStubFamily', 'PIC18'),
        processor: config.get('zephyrStubProcessor', 'PIC18F_STUB'),
        writeAddress: config.get('zephyrStubWriteAddress', '0x10'),
        writeHex: config.get('zephyrStubWriteHex', '01020304'),
    };
}
//# sourceMappingURL=settings.js.map