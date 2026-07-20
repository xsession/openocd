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
exports.registerSidebarViews = registerSidebarViews;
const vscode = __importStar(require("vscode"));
const hardware_1 = require("./hardware");
const utils_1 = require("./utils");
class SidebarItem extends vscode.TreeItem {
    constructor(label, collapsibleState = vscode.TreeItemCollapsibleState.None, children) {
        super(label, collapsibleState);
        this.children = children;
    }
}
class DynamicSidebarProvider {
    constructor(buildItems) {
        this.buildItems = buildItems;
        this.onDidChangeTreeDataEmitter = new vscode.EventEmitter();
        this.onDidChangeTreeData = this.onDidChangeTreeDataEmitter.event;
    }
    refresh() {
        this.onDidChangeTreeDataEmitter.fire(undefined);
    }
    getTreeItem(element) {
        return element;
    }
    async getChildren(element) {
        if (element) {
            return element.children ?? [];
        }
        return this.buildItems();
    }
}
function createSidebarAction(label, commandId, description, iconId, enabled = true, disabledReason) {
    const item = new SidebarItem(label);
    item.description = enabled ? description : disabledReason ?? description;
    item.tooltip = enabled ? description : disabledReason ?? description;
    item.iconPath = new vscode.ThemeIcon(enabled ? iconId : 'circle-slash');
    if (enabled) {
        item.command = { command: commandId, title: label };
    }
    return item;
}
function createSidebarStatus(label, description, iconId, commandId, tooltip) {
    const item = new SidebarItem(label);
    item.description = description;
    item.tooltip = tooltip ?? description;
    item.iconPath = new vscode.ThemeIcon(iconId);
    if (commandId) {
        item.command = { command: commandId, title: label };
    }
    return item;
}
function createSidebarGroup(label, children, expanded = true, iconId = 'folder') {
    const item = new SidebarItem(label, expanded ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.Collapsed, children);
    item.iconPath = new vscode.ThemeIcon(iconId);
    return item;
}
function formatAddress(address) {
    return `0x${address.toString(16).toUpperCase()}`;
}
async function tryGetHardwareStatus(backend) {
    try {
        return await backend.request('hardwareSessionStatus', {}, { recordError: false });
    }
    catch {
        return undefined;
    }
}
async function tryGetSimulatorStatus(backend) {
    try {
        return await backend.request('getStatus', {}, { recordError: false });
    }
    catch {
        return undefined;
    }
}
async function tryListBreakpoints(backend) {
    try {
        return await backend.request('listBreakpoints', {}, { recordError: false });
    }
    catch {
        return [];
    }
}
function buildRecentErrorGroup(backend) {
    const errors = backend.getRecentErrors(5);
    if (errors.length === 0) {
        return createSidebarGroup('Recent Backend Errors', [
            createSidebarStatus('No recent errors', 'Backend command failures will appear here', 'pass'),
        ], false, 'warning');
    }
    return createSidebarGroup('Recent Backend Errors', errors.map((message, index) => createSidebarStatus(`Error ${index + 1}`, message, 'error', 'openMicrochipTools.showOutputChannel', message)), false, 'warning');
}
async function buildHardwareSidebarItems(backend) {
    const status = await tryGetHardwareStatus(backend);
    const sessionActive = Boolean(status?.processor);
    const disabledReason = 'Requires an active hardware session';
    const sessionItem = sessionActive
        ? createSidebarStatus(status?.processor ?? 'Hardware session', status?.familyMetadata ? (0, hardware_1.summarizeFamily)(status.familyMetadata) : (status?.family ?? 'session active'), 'vm-active', 'openMicrochipTools.showHardwareSessionStatus', status?.familyMetadata ? (0, hardware_1.formatFamilyMetadata)(status.familyMetadata) : undefined)
        : createSidebarStatus('No hardware session', 'Start a script-backed hardware session', 'debug-disconnect', 'openMicrochipTools.startHardwareSession');
    return [
        createSidebarGroup('Session', [
            sessionItem,
            createSidebarAction('Start Hardware Session', 'openMicrochipTools.startHardwareSession', 'Create a hardware session', 'debug-start'),
            createSidebarAction('Browse Hardware Families', 'openMicrochipTools.listHardwareFamilies', 'Open family inventory and launch from it', 'list-tree'),
            createSidebarAction('End Hardware Session', 'openMicrochipTools.endHardwareSession', 'Close the active hardware session', 'debug-stop', sessionActive, disabledReason),
        ], true, 'radio-tower'),
        createSidebarGroup('Control', [
            createSidebarAction('Enter Debug Mode', 'openMicrochipTools.enterHardwareDebugMode', 'Switch the target into RI4 debug mode', 'debug-alt', sessionActive, disabledReason),
            createSidebarAction('Show Program Counter', 'openMicrochipTools.showHardwarePc', 'Read the current program counter', 'symbol-numeric', sessionActive, disabledReason),
            createSidebarAction('Set Program Counter', 'openMicrochipTools.setHardwarePc', 'Write a new program counter value', 'edit', sessionActive, disabledReason),
            createSidebarAction('Run Target', 'openMicrochipTools.runHardware', 'Resume target execution', 'play', sessionActive, disabledReason),
            createSidebarAction('Single Step', 'openMicrochipTools.stepHardware', 'Single-step the target', 'debug-step-over', sessionActive, disabledReason),
            createSidebarAction('Halt Target', 'openMicrochipTools.haltHardware', 'Halt the active hardware target', 'debug-pause', sessionActive, disabledReason),
            createSidebarAction('Program HEX or ELF', 'openMicrochipTools.programHardwareHex', 'Program firmware through the active session', 'arrow-circle-up', sessionActive, disabledReason),
        ], true, 'tools'),
        createSidebarGroup('Probe', [
            createSidebarAction('Probe PICkit 4', 'openMicrochipTools.probePickit4', 'Query the configured PICkit 4 target', 'plug'),
            createSidebarAction('Probe ICD4', 'openMicrochipTools.probeIcd4', 'Query the configured ICD4 target', 'plug'),
        ], false, 'plug'),
        buildRecentErrorGroup(backend),
    ];
}
async function buildHardwareControlSidebarItems(backend) {
    return (await buildHardwareSidebarItems(backend)).find((item) => item.label === 'Control')?.children ?? [];
}
function buildSimulatorSessionItem(status, sessionActive) {
    if (!sessionActive) {
        return createSidebarStatus('No simulator session', 'Start a simulator session and load firmware', 'debug-disconnect', 'openMicrochipTools.startSimulatorSession');
    }
    const parts = [];
    if (typeof status?.pc === 'number') {
        parts.push(`PC ${formatAddress(status.pc)}`);
    }
    if (typeof status?.instructions_per_second === 'number') {
        parts.push(`${Math.round(status.instructions_per_second)} ips`);
    }
    if (typeof status?.firmware_loaded === 'boolean') {
        parts.push(status.firmware_loaded ? 'firmware loaded' : 'no firmware');
    }
    return createSidebarStatus(status?.device?.name?.trim() ? status.device.name : 'Simulator session', parts.join(' | ') || 'Status available', 'vm-active', 'openMicrochipTools.showSimulatorStatus', (0, utils_1.stringify)(status));
}
function buildSimulatorRegisterGroup(status) {
    if (!status) {
        return createSidebarGroup('Registers', [
            createSidebarStatus('No register state', 'Start a simulator session to inspect registers', 'circle-slash'),
        ], true, 'symbol-numeric');
    }
    const items = [];
    if (typeof status.pc === 'number') {
        items.push(createSidebarStatus('PC', formatAddress(status.pc), 'symbol-numeric'));
    }
    if (typeof status.instructions_per_second === 'number') {
        items.push(createSidebarStatus('Instruction Rate', `${Math.round(status.instructions_per_second)} ips`, 'dashboard'));
    }
    items.push(createSidebarStatus('Firmware', status.firmware_loaded ? 'loaded' : 'not loaded', status.firmware_loaded ? 'check' : 'circle-large-outline'));
    return createSidebarGroup('Registers', items, true, 'symbol-numeric');
}
function buildSimulatorBreakpointGroup(breakpoints) {
    if (breakpoints.length === 0) {
        return createSidebarGroup('Breakpoints', [
            createSidebarStatus('No breakpoints', 'Use Add Breakpoint to create one', 'debug-breakpoint-disabled'),
        ], true, 'debug-breakpoint');
    }
    return createSidebarGroup('Breakpoints', breakpoints.map((address) => createSidebarStatus(formatAddress(address), 'Active simulator breakpoint', 'debug-breakpoint')), true, 'debug-breakpoint');
}
function buildTraceGroup(status) {
    const trace = status?.trace ?? [];
    if (trace.length === 0) {
        return createSidebarGroup('Recent Trace', [
            createSidebarStatus('No recent trace', 'Run or step the simulator to populate execution trace', 'history'),
        ], false, 'history');
    }
    return createSidebarGroup('Recent Trace', trace.slice(-5).reverse().map((entry, index) => {
        const label = typeof entry.pc === 'number' ? formatAddress(entry.pc) : `Trace ${index + 1}`;
        return createSidebarStatus(label, entry.bytes_hex ? `bytes ${entry.bytes_hex}` : 'no bytes recorded', 'history');
    }), false, 'history');
}
async function buildSimulatorSidebarItems(backend) {
    const status = await tryGetSimulatorStatus(backend);
    const breakpoints = await tryListBreakpoints(backend);
    const sessionActive = Boolean(status?.device);
    const disabledReason = 'Requires an active simulator session';
    return [
        createSidebarGroup('Session', [
            buildSimulatorSessionItem(status, sessionActive),
            createSidebarAction('Start Simulator Session', 'openMicrochipTools.startSimulatorSession', 'Select a device and firmware image', 'vm'),
            createSidebarAction('Show Simulator Status', 'openMicrochipTools.showSimulatorStatus', 'Inspect simulator state', 'pulse', sessionActive, disabledReason),
        ], true, 'vm'),
        buildSimulatorRegisterGroup(status),
        buildSimulatorBreakpointGroup(breakpoints),
        buildTraceGroup(status),
        createSidebarGroup('Execution', [
            createSidebarAction('Run Simulator', 'openMicrochipTools.runSimulator', 'Run for the configured instruction budget', 'play', sessionActive, disabledReason),
            createSidebarAction('Single Step', 'openMicrochipTools.stepSimulator', 'Execute one instruction', 'debug-step-over', sessionActive, disabledReason),
            createSidebarAction('Halt Simulator', 'openMicrochipTools.haltSimulator', 'Pause simulated execution', 'debug-pause', sessionActive, disabledReason),
            createSidebarAction('Add Breakpoint', 'openMicrochipTools.addBreakpoint', 'Insert a breakpoint by address', 'debug-breakpoint', sessionActive, disabledReason),
        ], true, 'run-all'),
        buildRecentErrorGroup(backend),
    ];
}
async function buildToolsSidebarItems(backend) {
    return [
        createSidebarGroup('Utilities', [
            createSidebarAction('List Known Devices', 'openMicrochipTools.listDevices', 'Browse repo-known device names', 'device-desktop'),
            createSidebarAction('Zephyr Stub Demo', 'openMicrochipTools.runZephyrStubDemo', 'Open the stub demo workbench panel', 'beaker'),
            createSidebarAction('Show Output Channel', 'openMicrochipTools.showOutputChannel', 'Show backend logs and responses', 'output'),
            createSidebarAction('Refresh Sidebar', 'openMicrochipTools.refreshViews', 'Reload current hardware and simulator summaries', 'refresh'),
            createSidebarAction('Clear Recent Errors', 'openMicrochipTools.clearRecentErrors', 'Clear the sidebar backend error list', 'clear-all', backend.getRecentErrors(1).length > 0, 'No recent backend errors'),
        ], true, 'wrench'),
        buildRecentErrorGroup(backend),
    ];
}
function registerSidebarViews(context, backend) {
    const hardwareProvider = new DynamicSidebarProvider(() => buildHardwareSidebarItems(backend));
    const hardwareControlProvider = new DynamicSidebarProvider(() => buildHardwareControlSidebarItems(backend));
    const simulatorProvider = new DynamicSidebarProvider(() => buildSimulatorSidebarItems(backend));
    const toolsProvider = new DynamicSidebarProvider(() => buildToolsSidebarItems(backend));
    context.subscriptions.push(vscode.window.registerTreeDataProvider('openMicrochipTools.hardwareView', hardwareProvider), vscode.window.registerTreeDataProvider('openMicrochipTools.hardwareControlView', hardwareControlProvider), vscode.window.registerTreeDataProvider('openMicrochipTools.simulatorView', simulatorProvider), vscode.window.registerTreeDataProvider('openMicrochipTools.toolsView', toolsProvider));
    return async () => {
        const hardwareStatus = await tryGetHardwareStatus(backend);
        await vscode.commands.executeCommand('setContext', 'openMicrochipTools.hardwareSessionActive', Boolean(hardwareStatus?.processor));
        const simulatorStatus = await tryGetSimulatorStatus(backend);
        await vscode.commands.executeCommand('setContext', 'openMicrochipTools.simulatorSessionActive', Boolean(simulatorStatus?.device));
        await vscode.commands.executeCommand('setContext', 'openMicrochipTools.hasRecentErrors', backend.getRecentErrors(1).length > 0);
        hardwareProvider.refresh();
        hardwareControlProvider.refresh();
        simulatorProvider.refresh();
        toolsProvider.refresh();
    };
}
//# sourceMappingURL=sidebar.js.map