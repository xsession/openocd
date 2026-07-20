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
exports.promptForFirmware = promptForFirmware;
exports.promptForAddress = promptForAddress;
exports.promptForPath = promptForPath;
exports.promptForTool = promptForTool;
const vscode = __importStar(require("vscode"));
async function promptForFirmware() {
    const pick = await vscode.window.showOpenDialog({
        canSelectMany: false,
        filters: {
            Firmware: ['hex', 'elf'],
        },
    });
    return pick?.[0]?.fsPath;
}
async function promptForAddress(label) {
    const value = await vscode.window.showInputBox({ prompt: label, placeHolder: '0x0' });
    if (!value) {
        return undefined;
    }
    return Number.parseInt(value, 0);
}
async function promptForPath(title, filters) {
    const pick = await vscode.window.showOpenDialog({ canSelectMany: false, title, filters });
    return pick?.[0]?.fsPath;
}
async function promptForTool() {
    const choice = await vscode.window.showQuickPick([
        { label: 'PICkit 4', value: 'pk4' },
        { label: 'ICD4', value: 'icd4' },
    ], { title: 'Select hardware tool' });
    return choice?.value;
}
//# sourceMappingURL=prompts.js.map