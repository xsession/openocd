import * as vscode from 'vscode';

import { type HardwareSessionStartOptions, type ZephyrStubDemoDefaults } from './types';

export async function persistHardwareSessionDefaults(options: HardwareSessionStartOptions): Promise<void> {
  const config = vscode.workspace.getConfiguration('openMicrochipTools');
  await Promise.all([
    config.update('hardwareProcessor', options.processor ?? '', vscode.ConfigurationTarget.Workspace),
    config.update('hardwareScriptsPath', options.scriptsPath ?? '', vscode.ConfigurationTarget.Workspace),
    config.update('hardwareToolScriptsPath', options.toolScriptsPath ?? '', vscode.ConfigurationTarget.Workspace),
  ]);
}

export async function persistZephyrStubDemoDefaults(options: ZephyrStubDemoDefaults): Promise<void> {
  const config = vscode.workspace.getConfiguration('openMicrochipTools');
  await Promise.all([
    config.update('zephyrStubFamily', options.family, vscode.ConfigurationTarget.Workspace),
    config.update('zephyrStubProcessor', options.processor, vscode.ConfigurationTarget.Workspace),
    config.update('zephyrStubWriteAddress', options.writeAddress, vscode.ConfigurationTarget.Workspace),
    config.update('zephyrStubWriteHex', options.writeHex, vscode.ConfigurationTarget.Workspace),
  ]);
}

export function loadZephyrStubDemoDefaults(): ZephyrStubDemoDefaults {
  const config = vscode.workspace.getConfiguration('openMicrochipTools');
  return {
    family: config.get<string>('zephyrStubFamily', 'PIC18'),
    processor: config.get<string>('zephyrStubProcessor', 'PIC18F_STUB'),
    writeAddress: config.get<string>('zephyrStubWriteAddress', '0x10'),
    writeHex: config.get<string>('zephyrStubWriteHex', '01020304'),
  };
}