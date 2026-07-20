import * as vscode from 'vscode';

import { BackendClient } from './backendClient';
import { showFamilyInventoryPanel } from './familyInventoryPanel';
import { formatFamilyMetadata, startHardwareSessionFlow, summarizeFamily } from './hardware';
import { promptForAddress, promptForFirmware, promptForPath } from './prompts';
import { type HardwareSessionStatus } from './types';
import { showZephyrStubDemoPanel } from './zephyrStubDemoPanel';

export async function registerCommands(
  context: vscode.ExtensionContext,
  backend: BackendClient,
  refreshViews: () => Promise<void>,
): Promise<void> {
  const command = (name: string, callback: () => Promise<void>) => {
    context.subscriptions.push(vscode.commands.registerCommand(name, async () => {
      try {
        await callback();
      } finally {
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
    const devices = await backend.request('listDevices', { prefix }) as string[];
    backend.show();
    backend.log(devices);
    void vscode.window.showQuickPick(devices, { title: 'Known devices' });
  });

  const probe = async (tool: 'pk4' | 'icd4') => {
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    const vid = await vscode.window.showInputBox({
      prompt: `${tool.toUpperCase()} VID`,
      value: config.get<string>(tool === 'pk4' ? 'pickit4Vid' : 'icd4Vid', '0x04D8'),
    });
    if (!vid) {
      return;
    }
    const pid = await vscode.window.showInputBox({
      prompt: `${tool.toUpperCase()} PID`,
      value: config.get<string>(tool === 'pk4' ? 'pickit4Pid' : 'icd4Pid', '0x0000'),
    });
    if (!pid) {
      return;
    }
    const keys = config.get<string[]>('statusKeys', ['Commands in progress']);
    const result = await backend.request('probeTool', { tool, vid, pid, keys });
    backend.show();
    backend.log(result);
    void vscode.window.showInformationMessage(`${tool.toUpperCase()} probe completed. See output channel for details.`);
  };

  command('openMicrochipTools.probePickit4', async () => probe('pk4'));
  command('openMicrochipTools.probeIcd4', async () => probe('icd4'));

  command('openMicrochipTools.runZephyrStubDemo', async () => {
    await showZephyrStubDemoPanel(backend, refreshViews);
  });

  command('openMicrochipTools.listHardwareFamilies', async () => {
    await showFamilyInventoryPanel(backend, refreshViews);
  });

  command('openMicrochipTools.startHardwareSession', async () => {
    await startHardwareSessionFlow(backend);
  });

  command('openMicrochipTools.showHardwareSessionStatus', async () => {
    const status = await backend.request('hardwareSessionStatus', {}) as HardwareSessionStatus;
    backend.show();
    backend.log(status);
    if (status.familyMetadata) {
      backend.log(formatFamilyMetadata(status.familyMetadata));
      void vscode.window.showInformationMessage(`${status.processor ?? 'Hardware session'}: ${summarizeFamily(status.familyMetadata)}`);
      return;
    }
    void vscode.window.showInformationMessage(`Hardware session active for ${status.processor ?? 'unknown processor'}.`);
  });

  command('openMicrochipTools.endHardwareSession', async () => {
    const result = await backend.request('hardwareEndSession', {}) as { closed?: boolean; previousSession?: HardwareSessionStatus };
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
    const result = await backend.request('hardwareGetPc', {}) as { pc?: number };
    backend.show();
    backend.log(result);
    if (typeof result.pc === 'number') {
      void vscode.window.showInformationMessage(`PC = 0x${result.pc.toString(16).toUpperCase()}`);
    }
  });

  command('openMicrochipTools.setHardwarePc', async () => {
    const address = await promptForAddress('Program counter address');
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
    const imagePath = await promptForPath('Select HEX or ELF image', { Firmware: ['hex', 'ihex', 'elf'] });
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
    const defaultDevice = config.get<string>('defaultDevice', 'PIC16F1509');
    const device = await vscode.window.showInputBox({ prompt: 'Device name', value: defaultDevice });
    if (!device) {
      return;
    }
    const firmware = await promptForFirmware();
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
    const maxSteps = vscode.workspace.getConfiguration('openMicrochipTools').get<number>('simulatorMaxSteps', 10000);
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
    const address = await promptForAddress('Breakpoint address');
    if (address === undefined || Number.isNaN(address)) {
      return;
    }
    const status = await backend.request('addBreakpoint', { address });
    backend.show();
    backend.log(status);
  });
}
