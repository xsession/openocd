import * as vscode from 'vscode';

import { BackendClient } from './backendClient';
import { loadZephyrStubDemoDefaults, persistZephyrStubDemoDefaults } from './settings';
import { type ZephyrStubDemoMessage } from './types';
import { stringify } from './utils';

function renderZephyrStubDemoHtml(initialValues: { family: string; processor: string; writeAddress: string; writeHex: string }): string {
  const safe = JSON.stringify(initialValues).replace(/</g, '\\u003c');
  return `<!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <style>
        :root {
          color-scheme: light dark;
          --bg: #121a22;
          --panel: rgba(25, 39, 52, 0.92);
          --ink: #e7eef5;
          --muted: #9bb0c2;
          --accent: #e09f3e;
          --accent-2: #9cd08f;
          --border: #31475c;
        }
        body {
          margin: 0;
          font-family: "Iowan Old Style", Georgia, serif;
          background: radial-gradient(circle at top left, #213447 0%, var(--bg) 60%);
          color: var(--ink);
        }
        main {
          max-width: 920px;
          margin: 0 auto;
          padding: 28px;
        }
        .panel {
          background: color-mix(in srgb, var(--panel) 92%, transparent);
          border: 1px solid var(--border);
          border-radius: 22px;
          padding: 24px;
          box-shadow: 0 18px 44px rgba(0, 0, 0, 0.22);
        }
        h1 {
          margin: 0 0 8px;
          font-size: 30px;
        }
        .lede {
          margin: 0 0 24px;
          color: var(--muted);
          max-width: 700px;
          line-height: 1.5;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
        }
        .field {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        label {
          color: var(--muted);
          font-size: 12px;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }
        input,
        select,
        button {
          border-radius: 14px;
          border: 1px solid var(--border);
          background: rgba(9, 16, 22, 0.68);
          color: var(--ink);
          padding: 12px 14px;
          font: inherit;
          box-sizing: border-box;
        }
        .actions {
          display: flex;
          gap: 12px;
          margin-top: 20px;
        }
        .cta {
          background: linear-gradient(135deg, var(--accent), #d66c3a);
          color: #111;
          border: none;
          font-weight: 700;
        }
        .ghost {
          background: transparent;
        }
        .status {
          min-height: 22px;
          margin-top: 18px;
          color: var(--accent-2);
          font-size: 13px;
        }
        .result {
          margin-top: 18px;
          padding: 16px;
          border-radius: 16px;
          border: 1px solid var(--border);
          background: rgba(6, 11, 16, 0.58);
          color: var(--ink);
          font-family: Consolas, "Courier New", monospace;
          font-size: 12px;
          line-height: 1.5;
          white-space: pre-wrap;
          overflow-x: auto;
        }
        .notes {
          margin-top: 22px;
          padding: 16px;
          border-radius: 16px;
          background: rgba(8, 14, 20, 0.4);
          border: 1px solid var(--border);
          color: var(--muted);
          line-height: 1.5;
        }
        @media (max-width: 780px) {
          .grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
    </head>
    <body>
      <main>
        <section class="panel">
          <h1>Zephyr Stub Demo</h1>
          <p class="lede">Run the repo-local RI4 stub session against a modeled family without leaving VS Code. The form persists defaults so you can iterate on a target quickly.</p>
          <div class="grid">
            <div class="field">
              <label for="family">Family</label>
              <select id="family">
                <option value="PIC18">PIC18</option>
                <option value="PIC16Enhanced">PIC16Enhanced</option>
                <option value="ARM_MPU">ARM_MPU</option>
                <option value="PIC32MZ">PIC32MZ</option>
                <option value="DSPIC30F">DSPIC30F</option>
                <option value="DSPIC33FJ">DSPIC33FJ</option>
                <option value="DSPIC33EP">DSPIC33EP</option>
                <option value="DSPIC33A">DSPIC33A</option>
                <option value="AVR">AVR</option>
              </select>
            </div>
            <div class="field">
              <label for="processor">Processor</label>
              <input id="processor" type="text" />
            </div>
            <div class="field">
              <label for="writeAddress">Write address</label>
              <input id="writeAddress" type="text" />
            </div>
            <div class="field">
              <label for="writeHex">Write payload hex</label>
              <input id="writeHex" type="text" />
            </div>
          </div>
          <div class="actions">
            <button id="run" class="cta" type="button">Run stub demo</button>
            <button id="reset" class="ghost" type="button">Reset defaults</button>
          </div>
          <div id="status" class="status"></div>
          <pre id="result" class="result">Run the demo to inspect the latest backend response here.</pre>
          <div class="notes">Current modeled paths: PIC18 TMOD, PIC16Enhanced config/test-memory flow, ARM_MPU flashless RAM/debug, PIC32MZ PE-style programming, DSPIC30F and DSPIC33FJ/EP PE-style programming, DSPIC33A DE-style programming, and AVR prog-mode/debug entry.</div>
        </section>
      </main>
      <script>
        const vscode = acquireVsCodeApi();
        const defaults = ${safe};
        const processorDefaults = {
          PIC18: 'PIC18F_STUB',
          PIC16Enhanced: 'PIC16F1509_STUB',
          ARM_MPU: 'ATSAME70_STUB',
          PIC32MZ: 'PIC32MZ2048EFH_STUB',
          DSPIC30F: 'DSPIC30F5011_STUB',
          DSPIC33FJ: 'DSPIC33FJ256GP710A_STUB',
          DSPIC33EP: 'DSPIC33EP512MU810_STUB',
          DSPIC33A: 'DSPIC33AK128MC106_STUB',
          AVR: 'ATMEGA4809_STUB',
        };

        const family = document.getElementById('family');
        const processor = document.getElementById('processor');
        const writeAddress = document.getElementById('writeAddress');
        const writeHex = document.getElementById('writeHex');
        const status = document.getElementById('status');
        const result = document.getElementById('result');

        function state() {
          return {
            family: family.value,
            processor: processor.value,
            writeAddress: writeAddress.value,
            writeHex: writeHex.value,
          };
        }

        function applyValues(values) {
          family.value = values.family;
          processor.value = values.processor;
          writeAddress.value = values.writeAddress;
          writeHex.value = values.writeHex;
        }

        function persist() {
          const current = state();
          vscode.setState(current);
          vscode.postMessage({ command: 'saveZephyrStubDefaults', ...current });
        }

        family.addEventListener('change', () => {
          const suggestedProcessor = processorDefaults[family.value] || '';
          if (!processor.value || Object.values(processorDefaults).includes(processor.value)) {
            processor.value = suggestedProcessor;
          }
          persist();
        });

        [processor, writeAddress, writeHex].forEach((input) => {
          input.addEventListener('input', persist);
        });

        document.getElementById('reset').addEventListener('click', () => {
          applyValues(defaults);
          status.textContent = 'Defaults restored.';
          result.textContent = 'Run the demo to inspect the latest backend response here.';
          persist();
        });

        document.getElementById('run').addEventListener('click', () => {
          status.textContent = 'Running stub demo...';
          result.textContent = 'Waiting for backend response...';
          persist();
          vscode.postMessage({ command: 'runZephyrStubDemo', ...state() });
        });

        window.addEventListener('message', (event) => {
          const message = event.data || {};
          if (message.command === 'demoCompleted') {
            status.textContent = message.summary || 'Stub demo completed.';
            result.textContent = message.resultText || 'No result payload returned.';
            return;
          }
          if (message.command === 'demoFailed') {
            status.textContent = message.error || 'Stub demo failed.';
            result.textContent = message.error || 'Stub demo failed.';
          }
        });

        applyValues({ ...defaults, ...(vscode.getState() || {}) });
        persist();
      </script>
    </body>
  </html>`;
}

export async function showZephyrStubDemoPanel(backend: BackendClient, refreshViews?: () => Promise<void>): Promise<void> {
  const initialValues = loadZephyrStubDemoDefaults();
  const panel = vscode.window.createWebviewPanel(
    'openMicrochipTools.zephyrStubDemo',
    'Open Microchip Tools: Zephyr Stub Demo',
    vscode.ViewColumn.Active,
    { enableFindWidget: false, enableScripts: true },
  );

  panel.webview.html = renderZephyrStubDemoHtml(initialValues);

  panel.webview.onDidReceiveMessage(async (message: ZephyrStubDemoMessage) => {
    if (message.command === 'saveZephyrStubDefaults') {
      await persistZephyrStubDemoDefaults({
        family: message.family ?? initialValues.family,
        processor: message.processor ?? initialValues.processor,
        writeAddress: message.writeAddress ?? initialValues.writeAddress,
        writeHex: message.writeHex ?? initialValues.writeHex,
      });
      return;
    }

    if (message.command !== 'runZephyrStubDemo') {
      return;
    }

    try {
      await persistZephyrStubDemoDefaults({
        family: message.family ?? initialValues.family,
        processor: message.processor ?? initialValues.processor,
        writeAddress: message.writeAddress ?? initialValues.writeAddress,
        writeHex: message.writeHex ?? initialValues.writeHex,
      });
      const runResult = await backend.request('runZephyrStubDemo', {
        family: message.family,
        processor: message.processor,
        writeAddress: message.writeAddress,
        writeHex: message.writeHex,
      }) as Record<string, unknown>;
      backend.show();
      backend.log(runResult);
      await refreshViews?.();
      const summary = `Stub demo completed for ${String(runResult.family ?? message.family ?? 'unknown family')}.`;
      void panel.webview.postMessage({ command: 'demoCompleted', summary, resultText: stringify(runResult) });
      void vscode.window.showInformationMessage(summary);
    } catch (err) {
      const text = err instanceof Error ? err.message : String(err);
      backend.show();
      backend.log({ error: text, family: message.family, processor: message.processor });
      void panel.webview.postMessage({ command: 'demoFailed', error: text });
      void vscode.window.showErrorMessage(`Zephyr stub demo failed: ${text}`);
    }
  });
}
