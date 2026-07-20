import * as vscode from 'vscode';

import { BackendClient } from './backendClient';
import { registerCommands } from './commands';
import { registerSidebarViews } from './sidebar';

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const backend = new BackendClient(context);
  context.subscriptions.push(backend);
  const refreshViews = registerSidebarViews(context, backend);
  await registerCommands(context, backend, refreshViews);
  await refreshViews();
}

export function deactivate(): void {
}