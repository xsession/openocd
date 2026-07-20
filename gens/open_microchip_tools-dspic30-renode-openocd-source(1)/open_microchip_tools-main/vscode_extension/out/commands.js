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
exports.registerCommands = registerCommands;
const vscode = __importStar(require("vscode"));
const familyInventoryPanel_1 = require("./familyInventoryPanel");
const hardware_1 = require("./hardware");
const prompts_1 = require("./prompts");
const zephyrStubDemoPanel_1 = require("./zephyrStubDemoPanel");
async function registerCommands(context, backend, refreshViews) {
    const command = (name, callback) => {
        context.subscriptions.push(vscode.commands.registerCommand(name, async () => {
            try {
                await callback();
            }
            finally {
                await refreshViews();
            }
        }));
    };
    command('openMicrochipTools.refreshViews', async () => {
        await refreshViews();
    });
    command('openMicrochipTools.showOutputChannel', async () => {
        backend.show();
    });
    command('openMicrochipTools.clearRecentErrors', async () => {
        backend.clearRecentErrors();
    });
    command('openMicrochipTools.listDevices', async () => {
        const prefix = await vscode.window.showInputBox({ prompt: 'Optional device prefix filter', value: '' });
        if (prefix === undefined) {
            return;
        }
        const devices = await backend.request('listDevices', { prefix });
        backend.show();
        backend.log(devices);
        void vscode.window.showQuickPick(devices, { title: 'Known devices' });
    });
    const probe = async (tool) => {
        const config = vscode.workspace.getConfiguration('openMicrochipTools');
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
        const keys = config.get('statusKeys', ['Commands in progress']);
        const result = await backend.request('probeTool', { tool, vid, pid, keys });
        backend.show();
        backend.log(result);
        void vscode.window.showInformationMessage(`${tool.toUpperCase()} probe completed. See output channel for details.`);
    };
    command('openMicrochipTools.probePickit4', async () => probe('pk4'));
    command('openMicrochipTools.probeIcd4', async () => probe('icd4'));
    command('openMicrochipTools.runZephyrStubDemo', async () => {
        await (0, zephyrStubDemoPanel_1.showZephyrStubDemoPanel)(backend, refreshViews);
    });
    command('openMicrochipTools.listHardwareFamilies', async () => {
        await (0, familyInventoryPanel_1.showFamilyInventoryPanel)(backend, refreshViews);
    });
    command('openMicrochipTools.startHardwareSession', async () => {
        await (0, hardware_1.startHardwareSessionFlow)(backend);
    });
    command('openMicrochipTools.showHardwareSessionStatus', async () => {
        const status = await backend.request('hardwareSessionStatus', {});
        backend.show();
        backend.log(status);
        if (status.familyMetadata) {
            backend.log((0, hardware_1.formatFamilyMetadata)(status.familyMetadata));
            void vscode.window.showInformationMessage(`${status.processor ?? 'Hardware session'}: ${(0, hardware_1.summarizeFamily)(status.familyMetadata)}`);
            return;
        }
        void vscode.window.showInformationMessage(`Hardware session active for ${status.processor ?? 'unknown processor'}.`);
    });
    command('openMicrochipTools.endHardwareSession', async () => {
        const result = await backend.request('hardwareEndSession', {});
        backend.show();
        backend.log(result);
        if (result.closed && result.previousSession) {
            void vscode.window.showInformationMessage(`Hardware session closed for ${result.previousSession.processor ?? 'unknown processor'}.`);
            return;
        }
        void vscode.window.showInformationMessage('No hardware session was active.');
    });
    command('openMicrochipTools.enterHardwareDebugMode', async () => {
        const result = await backend.request('hardwareEnterDebugMode', {});
        backend.show();
        backend.log(result);
    });
    command('openMicrochipTools.showHardwarePc', async () => {
        const result = await backend.request('hardwareGetPc', {});
        backend.show();
        backend.log(result);
        if (typeof result.pc === 'number') {
            void vscode.window.showInformationMessage(`PC = 0x${result.pc.toString(16).toUpperCase()}`);
        }
    });
    command('openMicrochipTools.setHardwarePc', async () => {
        const address = await (0, prompts_1.promptForAddress)('Program counter address');
        if (address === undefined || Number.isNaN(address)) {
            return;
        }
        const result = await backend.request('hardwareSetPc', { address });
        backend.show();
        backend.log(result);
    });
    command('openMicrochipTools.runHardware', async () => {
        const result = await backend.request('hardwareRun', {});
        backend.show();
        backend.log(result);
    });
    command('openMicrochipTools.stepHardware', async () => {
        const result = await backend.request('hardwareStep', {});
        backend.show();
        backend.log(result);
    });
    command('openMicrochipTools.haltHardware', async () => {
        const result = await backend.request('hardwareHalt', {});
        backend.show();
        backend.log(result);
    });
    command('openMicrochipTools.programHardwareHex', async () => {
        const imagePath = await (0, prompts_1.promptForPath)('Select HEX or ELF image', { Firmware: ['hex', 'ihex', 'elf'] });
        if (!imagePath) {
            return;
        }
        const verifyChoice = await vscode.window.showQuickPick(['No verify', 'Verify after write'], { title: 'Programming verification' });
        if (!verifyChoice) {
            return;
        }
        const result = await backend.request('hardwareProgramHex', {
            path: imagePath,
            eraseFirst: true,
            verify: verifyChoice === 'Verify after write',
        });
        backend.show();
        backend.log(result);
        void vscode.window.showInformationMessage('Hardware programming completed.');
    });
    command('openMicrochipTools.startSimulatorSession', async () => {
        const config = vscode.workspace.getConfiguration('openMicrochipTools');
        const defaultDevice = config.get('defaultDevice', 'PIC16F1509');
        const device = await vscode.window.showInputBox({ prompt: 'Device name', value: defaultDevice });
        if (!device) {
            return;
        }
        const firmware = await (0, prompts_1.promptForFirmware)();
        if (!firmware) {
            return;
        }
        await backend.request('initSession', { device });
        const status = await backend.request('loadFirmware', { path: firmware });
        backend.show();
        backend.log(status);
        void vscode.window.showInformationMessage(`Simulator session started for ${device}.`);
    });
    command('openMicrochipTools.showSimulatorStatus', async () => {
        const status = await backend.request('getStatus', {});
        backend.show();
        backend.log(status);
    });
    command('openMicrochipTools.stepSimulator', async () => {
        const status = await backend.request('step', {});
        backend.show();
        backend.log(status);
    });
    command('openMicrochipTools.runSimulator', async () => {
        const maxSteps = vscode.workspace.getConfiguration('openMicrochipTools').get('simulatorMaxSteps', 10000);
        const status = await backend.request('run', { maxSteps });
        backend.show();
        backend.log(status);
    });
    command('openMicrochipTools.haltSimulator', async () => {
        const status = await backend.request('halt', {});
        backend.show();
        backend.log(status);
    });
    command('openMicrochipTools.addBreakpoint', async () => {
        const address = await (0, prompts_1.promptForAddress)('Breakpoint address');
        if (address === undefined || Number.isNaN(address)) {
            return;
        }
        const status = await backend.request('addBreakpoint', { address });
        backend.show();
        backend.log(status);
    });
}
//# sourceMappingURL=commands.js.map