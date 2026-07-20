import * as vscode from 'vscode';

import { BackendClient } from './backendClient';
import { promptForPath, promptForTool } from './prompts';
import {
  type FamilyMetadata,
  type HardwareSessionStartOptions,
  type HardwareSessionStatus,
} from './types';

export function summarizeFamily(metadata: FamilyMetadata): string {
  const flags: string[] = [];
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

export function formatFamilyMetadata(metadata: FamilyMetadata): string {
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
    .filter((line): line is string => Boolean(line))
    .join('\n');
}

export async function promptForHardwareFamily(
  backend: BackendClient,
  configuredFamily: string,
): Promise<FamilyMetadata | undefined> {
  const families = await backend.request('listHardwareFamilies', {}) as FamilyMetadata[];
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

export async function startHardwareSessionFlow(
  backend: BackendClient,
  preferredFamily?: FamilyMetadata,
  preferredOptions?: HardwareSessionStartOptions,
): Promise<void> {
  const config = vscode.workspace.getConfiguration('openMicrochipTools');
  const tool = await promptForTool();
  if (!tool) {
    return;
  }

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

  const processor = await vscode.window.showInputBox({
    prompt: 'Processor name used in scripts.xml',
    value: preferredOptions?.processor || config.get<string>('hardwareProcessor', 'PIC16F1509'),
  });
  if (!processor) {
    return;
  }

  const selectedFamily = preferredFamily ?? await promptForHardwareFamily(backend, config.get<string>('hardwareFamily', ''));
  if (!selectedFamily) {
    return;
  }

  const configuredScripts = preferredOptions?.scriptsPath || config.get<string>('hardwareScriptsPath', '');
  const scriptsPath = configuredScripts || await promptForPath('Select scripts.xml', { XML: ['xml'] });
  if (!scriptsPath) {
    return;
  }

  const configuredToolScripts = preferredOptions?.toolScriptsPath || config.get<string>('hardwareToolScriptsPath', '');
  const scriptSuffix = config.get<string>('hardwareScriptSuffix', '');
  const pcBytes = config.get<number>('hardwarePcBytes', 4);
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
  }) as HardwareSessionStatus;
  backend.show();
  backend.log(status);
  if (status.familyMetadata) {
    backend.log(formatFamilyMetadata(status.familyMetadata));
  }
  void vscode.window.showInformationMessage(
    `Hardware session started for ${processor} (${selectedFamily.family}). ${status.familyMetadata ? summarizeFamily(status.familyMetadata) : ''}`.trim(),
  );
}