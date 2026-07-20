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
exports.summarizeFamily = summarizeFamily;
exports.formatFamilyMetadata = formatFamilyMetadata;
exports.promptForHardwareFamily = promptForHardwareFamily;
exports.startHardwareSessionFlow = startHardwareSessionFlow;
const vscode = __importStar(require("vscode"));
const prompts_1 = require("./prompts");
function summarizeFamily(metadata) {
    const flags = [];
    if (metadata.supportsProgramming) {
        flags.push('program');
    }
    if (metadata.supportsDebugging) {
        flags.push('debug');
    }
    if (metadata.supportsSetPc) {
        flags.push('set-pc');
    }
    const behavior = metadata.behavior ? `${metadata.behavior}` : 'unknown-behavior';
    const capabilityText = flags.length ? flags.join(', ') : 'no modeled capabilities';
    return `${behavior} | ${capabilityText}`;
}
function formatFamilyMetadata(metadata) {
    const rawTags = [
        ...(metadata.programmerRawCommandTags ?? []),
        ...(metadata.debuggerRawCommandTags ?? []),
    ];
    const rawGroups = [
        ...(metadata.programmerRawCommandGroups ?? []),
        ...(metadata.debuggerRawCommandGroups ?? []),
    ];
    const rawCapabilities = [
        ...(metadata.programmerRawCommandCapabilities ?? []),
        ...(metadata.debuggerRawCommandCapabilities ?? []),
    ];
    const rawSignatures = [
        ...(metadata.programmerRawCommandSignatures ?? []),
        ...(metadata.debuggerRawCommandSignatures ?? []),
    ];
    return [
        `Family: ${metadata.family}`,
        `Behavior: ${metadata.behavior ?? 'unknown'}`,
        `Programmer: ${metadata.programmerClass ?? 'unknown'}`,
        `Debugger: ${metadata.debuggerClass ?? 'unknown'}`,
        `Named scripts: ${metadata.namedScriptCount ?? 0}`,
        `Supports programming: ${metadata.supportsProgramming ? 'yes' : 'no'}`,
        `Supports debugging: ${metadata.supportsDebugging ? 'yes' : 'no'}`,
        `Supports SetPC: ${metadata.supportsSetPc ? 'yes' : 'no'}`,
        `Raw command groups: ${rawGroups.length ? rawGroups.join(', ') : 'none modeled'}`,
        `Raw command capabilities: ${rawCapabilities.length ? rawCapabilities.join(', ') : 'none modeled'}`,
        `Raw command signatures: ${rawSignatures.length ? rawSignatures.join(', ') : 'none modeled'}`,
        `Raw command tags: ${rawTags.length ? rawTags.join(', ') : 'none modeled'}`,
        metadata.notes ? `Notes: ${metadata.notes}` : undefined,
    ]
        .filter((line) => Boolean(line))
        .join('\n');
}
async function promptForHardwareFamily(backend, configuredFamily) {
    const families = await backend.request('listHardwareFamilies', {});
    const items = families.map((family) => ({
        label: family.family,
        description: summarizeFamily(family),
        detail: family.notes || `${family.programmerClass ?? 'Unknown programmer'} / ${family.debuggerClass ?? 'Unknown debugger'}`,
        family,
    }));
    const preferred = configuredFamily.trim().toUpperCase();
    const picked = await vscode.window.showQuickPick(items, {
        title: 'Select RI4 family',
        placeHolder: preferred || 'Choose the family that matches your processor/scripts.xml bundle',
    });
    if (!picked) {
        return undefined;
    }
    return picked.family;
}
async function startHardwareSessionFlow(backend, preferredFamily, preferredOptions) {
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    const tool = await (0, prompts_1.promptForTool)();
    if (!tool) {
        return;
    }
    const vid = await vscode.window.showInputBox({
        prompt: `${tool.toUpperCase()} VID`,
        value: config.get(tool === 'pk4' ? 'pickit4Vid' : 'icd4Vid', '0x04D8'),
    });
    if (!vid) {
        return;
    }
    const pid = await vscode.window.showInputBox({
        prompt: `${tool.toUpperCase()} PID`,
        value: config.get(tool === 'pk4' ? 'pickit4Pid' : 'icd4Pid', '0x0000'),
    });
    if (!pid) {
        return;
    }
    const processor = await vscode.window.showInputBox({
        prompt: 'Processor name used in scripts.xml',
        value: preferredOptions?.processor || config.get('hardwareProcessor', 'PIC16F1509'),
    });
    if (!processor) {
        return;
    }
    const selectedFamily = preferredFamily ?? await promptForHardwareFamily(backend, config.get('hardwareFamily', ''));
    if (!selectedFamily) {
        return;
    }
    const configuredScripts = preferredOptions?.scriptsPath || config.get('hardwareScriptsPath', '');
    const scriptsPath = configuredScripts || await (0, prompts_1.promptForPath)('Select scripts.xml', { XML: ['xml'] });
    if (!scriptsPath) {
        return;
    }
    const configuredToolScripts = preferredOptions?.toolScriptsPath || config.get('hardwareToolScriptsPath', '');
    const scriptSuffix = config.get('hardwareScriptSuffix', '');
    const pcBytes = config.get('hardwarePcBytes', 4);
    const status = await backend.request('hardwareStartSession', {
        tool,
        vid,
        pid,
        family: selectedFamily.family,
        processor,
        scriptsPath,
        toolScriptsPath: configuredToolScripts || undefined,
        scriptSuffix,
        pcBytes,
    });
    backend.show();
    backend.log(status);
    if (status.familyMetadata) {
        backend.log(formatFamilyMetadata(status.familyMetadata));
    }
    void vscode.window.showInformationMessage(`Hardware session started for ${processor} (${selectedFamily.family}). ${status.familyMetadata ? summarizeFamily(status.familyMetadata) : ''}`.trim());
}
//# sourceMappingURL=hardware.js.map