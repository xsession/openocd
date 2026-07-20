import * as vscode from 'vscode';

import { type ToolKind } from './types';

export async function promptForFirmware(): Promise<string | undefined> {
  const pick = await vscode.window.showOpenDialog({
    canSelectMany: false,
    filters: {
      Firmware: ['hex', 'elf'],
    },
  });
  return pick?.[0]?.fsPath;
}

export async function promptForAddress(label: string): Promise<number | undefined> {
  const value = await vscode.window.showInputBox({ prompt: label, placeHolder: '0x0' });
  if (!value) {
    return undefined;
  }
  return Number.parseInt(value, 0);
}

export async function promptForPath(title: string, filters: Record<string, string[]>): Promise<string | undefined> {
  const pick = await vscode.window.showOpenDialog({ canSelectMany: false, title, filters });
  return pick?.[0]?.fsPath;
}

export async function promptForTool(): Promise<ToolKind | undefined> {
  const choice = await vscode.window.showQuickPick(
    [
      { label: 'PICkit 4', value: 'pk4' as const },
      { label: 'ICD4', value: 'icd4' as const },
    ],
    { title: 'Select hardware tool' },
  );
  return choice?.value;
}