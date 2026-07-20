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
exports.showFamilyInventoryPanel = showFamilyInventoryPanel;
const vscode = __importStar(require("vscode"));
const hardware_1 = require("./hardware");
const prompts_1 = require("./prompts");
const settings_1 = require("./settings");
function renderFamilyInventoryHtml(families, initialOptions) {
    const familyJson = JSON.stringify(families).replace(/</g, '\\u003c');
    const initialOptionsJson = JSON.stringify(initialOptions).replace(/</g, '\\u003c');
    return `<!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <style>
        :root {
          color-scheme: light dark;
          --bg: #0f1720;
          --panel: rgba(22, 34, 49, 0.9);
          --panel-strong: rgba(14, 24, 35, 0.95);
          --ink: #e6edf5;
          --muted: #9db0c4;
          --accent: #74c69d;
          --accent-2: #f4a261;
          --chip: #233447;
          --border: #2c4258;
        }
        body {
          margin: 0;
          font-family: Georgia, "Palatino Linotype", serif;
          background: radial-gradient(circle at top, #1b2d3f, var(--bg) 55%);
          color: var(--ink);
        }
        main {
          max-width: 1220px;
          margin: 0 auto;
          padding: 28px;
        }
        h1 {
          margin: 0 0 8px;
          font-size: 30px;
        }
        .lede {
          margin: 0 0 18px;
          color: var(--muted);
          max-width: 840px;
          line-height: 1.5;
        }
        .shell {
          display: grid;
          gap: 16px;
        }
        .panel {
          border: 1px solid var(--border);
          border-radius: 20px;
          background: var(--panel);
          box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
          padding: 18px;
        }
        .context,
        .toolbar {
          display: grid;
          gap: 12px;
        }
        .context {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .toolbar {
          grid-template-columns: 2fr 2fr 1fr 1fr 1fr 1fr;
        }
        .field {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .field label {
          color: var(--muted);
          font-size: 12px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .field-row {
          display: flex;
          gap: 8px;
        }
        input,
        select,
        button {
          width: 100%;
          box-sizing: border-box;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: var(--panel-strong);
          color: var(--ink);
          padding: 12px 14px;
          font: inherit;
        }
        button {
          cursor: pointer;
        }
        .browse {
          width: auto;
          white-space: nowrap;
        }
        .summary {
          color: var(--muted);
          font-size: 13px;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 16px;
        }
        .card {
          border: 1px solid var(--border);
          border-radius: 18px;
          background: color-mix(in srgb, var(--panel) 92%, transparent);
          padding: 16px;
        }
        .card h2 {
          margin: 0;
          font-size: 20px;
        }
        .behavior {
          margin-top: 4px;
          color: var(--accent);
          font-size: 13px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .meta,
        .notes {
          color: var(--muted);
          font-size: 13px;
          line-height: 1.5;
        }
        .chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 12px 0;
        }
        .chip {
          border-radius: 999px;
          border: 1px solid var(--border);
          background: var(--chip);
          padding: 4px 10px;
          font-size: 12px;
        }
        .chip.signature {
          background: color-mix(in srgb, var(--accent-2) 22%, var(--chip));
        }
        .chip.subtle {
          color: var(--muted);
        }
        .actions {
          display: flex;
          gap: 10px;
          margin: 14px 0 10px;
        }
        .action {
          width: auto;
          border-color: var(--accent);
          background: transparent;
        }
        @media (max-width: 960px) {
          .context,
          .toolbar {
            grid-template-columns: 1fr;
          }
        }
      </style>
    </head>
    <body>
      <main>
        <h1>RI4 Family Inventory</h1>
        <p class="lede">Browse modeled families, filter by raw-command semantics, and launch a hardware script session with the processor and script paths already staged.</p>
        <div class="shell">
          <section class="panel context">
            <div class="field">
              <label for="processor">Processor</label>
              <input id="processor" type="text" placeholder="PIC16F1509" />
            </div>
            <div class="field">
              <label for="scriptsPath">scripts.xml</label>
              <div class="field-row">
                <input id="scriptsPath" type="text" placeholder="Path to scripts.xml" />
                <button id="browseScriptsPath" class="browse" type="button">Browse</button>
              </div>
            </div>
            <div class="field">
              <label for="toolScriptsPath">Tool scripts</label>
              <div class="field-row">
                <input id="toolScriptsPath" type="text" placeholder="Optional tool.xml path" />
                <button id="browseToolScriptsPath" class="browse" type="button">Browse</button>
              </div>
            </div>
          </section>
          <section class="panel toolbar">
            <input id="search" type="search" placeholder="Local search across notes and metadata" />
            <input id="prefixFilter" type="search" placeholder="Server-side family/class prefix" />
            <select id="behaviorFilter"><option value="all">All behaviors</option></select>
            <select id="groupFilter"><option value="all">All groups</option></select>
            <select id="signatureFilter"><option value="all">All signatures</option></select>
            <select id="capabilityFilter"><option value="all">All capabilities</option></select>
          </section>
          <div id="summary" class="summary"></div>
          <section id="grid" class="grid"></section>
        </div>
      </main>
      <script>
        const vscode = acquireVsCodeApi();
        const allFamilies = ${familyJson};
        const initialOptions = ${initialOptionsJson};
        const state = vscode.getState() || {};
        let serverFamilies = Array.isArray(state.families) ? state.families : allFamilies;
        let restoreScrollY = Number(state.scrollY || 0);
        let pendingServerRefresh = 0;
        let pendingDefaultsSave = 0;

        const grid = document.getElementById('grid');
        const summary = document.getElementById('summary');
        const search = document.getElementById('search');
        const prefixFilter = document.getElementById('prefixFilter');
        const behaviorFilter = document.getElementById('behaviorFilter');
        const groupFilter = document.getElementById('groupFilter');
        const signatureFilter = document.getElementById('signatureFilter');
        const capabilityFilter = document.getElementById('capabilityFilter');
        const processor = document.getElementById('processor');
        const scriptsPath = document.getElementById('scriptsPath');
        const toolScriptsPath = document.getElementById('toolScriptsPath');

        processor.value = initialOptions.processor || '';
        scriptsPath.value = initialOptions.scriptsPath || '';
        toolScriptsPath.value = initialOptions.toolScriptsPath || '';
        search.value = state.localSearch || '';
        prefixFilter.value = state.searchPrefix || '';

        function selectLabel(selectId, value) {
          if (value === 'all') {
            if (selectId === 'behaviorFilter') { return 'All behaviors'; }
            if (selectId === 'groupFilter') { return 'All groups'; }
            if (selectId === 'signatureFilter') { return 'All signatures'; }
            return 'All capabilities';
          }
          return value;
        }

        function optionsFor(values) {
          return ['all'].concat(Array.from(new Set(values.filter(Boolean))).sort());
        }

        function populateSelect(select, values, selected) {
          const current = selected || 'all';
          select.innerHTML = values.map((value) => '<option value="' + value + '">' + selectLabel(select.id, value) + '</option>').join('');
          select.value = values.includes(current) ? current : 'all';
        }

        populateSelect(behaviorFilter, optionsFor(allFamilies.map((family) => family.behavior || 'unknown-behavior')), state.behavior);
        populateSelect(groupFilter, optionsFor(allFamilies.flatMap((family) => [
          ...(family.programmerRawCommandGroups || []),
          ...(family.debuggerRawCommandGroups || []),
        ])), state.group);
        populateSelect(signatureFilter, optionsFor(allFamilies.flatMap((family) => [
          ...(family.programmerRawCommandSignatures || []),
          ...(family.debuggerRawCommandSignatures || []),
        ])), state.signature);
        populateSelect(capabilityFilter, optionsFor(allFamilies.flatMap((family) => [
          ...(family.programmerRawCommandCapabilities || []),
          ...(family.debuggerRawCommandCapabilities || []),
        ])), state.capability);

        function captureState() {
          vscode.setState({
            localSearch: search.value || '',
            searchPrefix: prefixFilter.value || '',
            behavior: behaviorFilter.value || 'all',
            group: groupFilter.value || 'all',
            signature: signatureFilter.value || 'all',
            capability: capabilityFilter.value || 'all',
            families: serverFamilies,
            scrollY: window.scrollY || 0,
          });
        }

        function familyCard(family) {
          const rawCapabilities = [
            ...(family.programmerRawCommandCapabilities || []),
            ...(family.debuggerRawCommandCapabilities || []),
          ];
          const rawSignatures = [
            ...(family.programmerRawCommandSignatures || []),
            ...(family.debuggerRawCommandSignatures || []),
          ];
          const rawGroups = [
            ...(family.programmerRawCommandGroups || []),
            ...(family.debuggerRawCommandGroups || []),
          ];
          const coreChips = [
            family.supportsProgramming ? 'program' : '',
            family.supportsDebugging ? 'debug' : '',
            family.supportsSetPc ? 'set-pc' : '',
          ].filter(Boolean);
          return ''
            + '<article class="card">'
            +   '<h2>' + family.family + '</h2>'
            +   '<div class="behavior">' + (family.behavior || 'unknown-behavior') + '</div>'
            +   '<div class="actions"><button class="action" type="button" data-family="' + family.family + '">Start session</button></div>'
            +   '<div class="chips">' + (coreChips.length ? coreChips.map((value) => '<span class="chip">' + value + '</span>').join('') : '<span class="chip subtle">no modeled capabilities</span>') + '</div>'
            +   '<p class="meta"><strong>Programmer:</strong> ' + (family.programmerClass || 'unknown') + '<br><strong>Debugger:</strong> ' + (family.debuggerClass || 'unknown') + '<br><strong>Named scripts:</strong> ' + (family.namedScriptCount || 0) + '</p>'
            +   '<p class="meta"><strong>Raw groups:</strong> ' + (rawGroups.length ? rawGroups.join(', ') : 'none') + '</p>'
            +   '<div class="chips">' + (rawSignatures.length ? rawSignatures.map((value) => '<span class="chip signature">' + value + '</span>').join('') : '<span class="chip subtle">no raw-command signatures</span>') + '</div>'
            +   '<div class="chips">' + (rawCapabilities.length ? rawCapabilities.map((value) => '<span class="chip subtle">' + value + '</span>').join('') : '<span class="chip subtle">no raw-command capabilities</span>') + '</div>'
            +   (family.notes ? '<p class="notes">' + family.notes + '</p>' : '')
            + '</article>';
        }

        function applyFilters() {
          const needle = (search.value || '').trim().toLowerCase();
          const behavior = behaviorFilter.value;
          const group = groupFilter.value;
          const signature = signatureFilter.value;
          const capability = capabilityFilter.value;
          const filtered = serverFamilies.filter((family) => {
            const groups = new Set([...(family.programmerRawCommandGroups || []), ...(family.debuggerRawCommandGroups || [])]);
            const signatures = new Set([...(family.programmerRawCommandSignatures || []), ...(family.debuggerRawCommandSignatures || [])]);
            const capabilities = new Set([...(family.programmerRawCommandCapabilities || []), ...(family.debuggerRawCommandCapabilities || [])]);
            const haystack = [
              family.family,
              family.behavior,
              family.programmerClass,
              family.debuggerClass,
              family.notes,
              ...Array.from(groups),
              ...Array.from(signatures),
              ...Array.from(capabilities),
            ].filter(Boolean).join(' ').toLowerCase();

            if (needle && !haystack.includes(needle)) {
              return false;
            }
            if (behavior !== 'all' && (family.behavior || 'unknown-behavior') !== behavior) {
              return false;
            }
            if (group !== 'all' && !groups.has(group)) {
              return false;
            }
            if (signature !== 'all' && !signatures.has(signature)) {
              return false;
            }
            if (capability !== 'all' && !capabilities.has(capability)) {
              return false;
            }
            return true;
          });

          grid.innerHTML = filtered.map(familyCard).join('');
          summary.textContent = filtered.length + ' of ' + serverFamilies.length + ' families shown';
          captureState();
          if (restoreScrollY) {
            const scrollY = restoreScrollY;
            restoreScrollY = 0;
            requestAnimationFrame(() => window.scrollTo(0, scrollY));
          }
        }

        function saveDefaults() {
          clearTimeout(pendingDefaultsSave);
          pendingDefaultsSave = window.setTimeout(() => {
            vscode.postMessage({
              command: 'saveHardwareDefaults',
              processor: processor.value || '',
              scriptsPath: scriptsPath.value || '',
              toolScriptsPath: toolScriptsPath.value || '',
            });
          }, 100);
        }

        function requestServerFamilies() {
          clearTimeout(pendingServerRefresh);
          pendingServerRefresh = window.setTimeout(() => {
            captureState();
            restoreScrollY = window.scrollY || 0;
            vscode.postMessage({
              command: 'refreshFamilies',
              searchPrefix: prefixFilter.value || '',
              group: groupFilter.value,
              signature: signatureFilter.value,
              capability: capabilityFilter.value,
            });
          }, 80);
        }

        search.addEventListener('input', applyFilters);
        prefixFilter.addEventListener('input', requestServerFamilies);
        behaviorFilter.addEventListener('change', applyFilters);
        groupFilter.addEventListener('change', requestServerFamilies);
        signatureFilter.addEventListener('change', requestServerFamilies);
        capabilityFilter.addEventListener('change', requestServerFamilies);
        processor.addEventListener('input', saveDefaults);
        scriptsPath.addEventListener('input', saveDefaults);
        toolScriptsPath.addEventListener('input', saveDefaults);
        window.addEventListener('scroll', captureState, { passive: true });

        document.getElementById('browseScriptsPath').addEventListener('click', () => {
          vscode.postMessage({ command: 'browsePath', field: 'scriptsPath' });
        });

        document.getElementById('browseToolScriptsPath').addEventListener('click', () => {
          vscode.postMessage({ command: 'browsePath', field: 'toolScriptsPath' });
        });

        grid.addEventListener('click', (event) => {
          const target = event.target;
          if (!(target instanceof HTMLElement)) {
            return;
          }
          const button = target.closest('button[data-family]');
          if (!(button instanceof HTMLButtonElement)) {
            return;
          }
          const family = button.getAttribute('data-family');
          if (!family) {
            return;
          }
          vscode.postMessage({
            command: 'startHardwareSession',
            family,
            processor: processor.value || '',
            scriptsPath: scriptsPath.value || '',
            toolScriptsPath: toolScriptsPath.value || '',
          });
        });

        window.addEventListener('message', (event) => {
          const message = event.data || {};
          if (message.command === 'setFieldValue' && message.field) {
            if (message.field === 'scriptsPath') {
              scriptsPath.value = message.value || '';
            }
            if (message.field === 'toolScriptsPath') {
              toolScriptsPath.value = message.value || '';
            }
            saveDefaults();
            return;
          }
          if (message.command === 'replaceFamilies' && Array.isArray(message.families)) {
            serverFamilies = message.families;
            applyFilters();
          }
        });

        if (prefixFilter.value || groupFilter.value !== 'all' || signatureFilter.value !== 'all' || capabilityFilter.value !== 'all') {
          requestServerFamilies();
        }
        applyFilters();
      </script>
    </body>
  </html>`;
}
async function showFamilyInventoryPanel(backend, refreshViews) {
    const families = await backend.request('listHardwareFamilies', {});
    const config = vscode.workspace.getConfiguration('openMicrochipTools');
    const initialOptions = {
        processor: config.get('hardwareProcessor', 'PIC16F1509'),
        scriptsPath: config.get('hardwareScriptsPath', ''),
        toolScriptsPath: config.get('hardwareToolScriptsPath', ''),
    };
    const panel = vscode.window.createWebviewPanel('openMicrochipTools.familyInventory', 'Open Microchip Tools: Family Inventory', vscode.ViewColumn.Active, { enableFindWidget: true, enableScripts: true });
    panel.webview.html = renderFamilyInventoryHtml(families, initialOptions);
    panel.webview.onDidReceiveMessage(async (message) => {
        if (message.command === 'saveHardwareDefaults') {
            await (0, settings_1.persistHardwareSessionDefaults)({
                processor: message.processor,
                scriptsPath: message.scriptsPath,
                toolScriptsPath: message.toolScriptsPath,
            });
            return;
        }
        if (message.command === 'browsePath' && message.field) {
            const title = message.field === 'scriptsPath' ? 'Select scripts.xml' : 'Select tool scripts XML';
            const selectedPath = await (0, prompts_1.promptForPath)(title, { XML: ['xml'] });
            if (selectedPath) {
                void panel.webview.postMessage({ command: 'setFieldValue', field: message.field, value: selectedPath });
            }
            return;
        }
        if (message.command === 'refreshFamilies') {
            const args = {};
            if (message.searchPrefix) {
                args.searchPrefix = message.searchPrefix;
            }
            if (message.group && message.group !== 'all') {
                args.groups = [message.group];
            }
            if (message.signature && message.signature !== 'all') {
                args.signatures = [message.signature];
            }
            if (message.capability && message.capability !== 'all') {
                args.capabilities = [message.capability];
            }
            const filteredFamilies = await backend.request('listHardwareFamilies', args, { recordError: false });
            void panel.webview.postMessage({ command: 'replaceFamilies', families: filteredFamilies });
            return;
        }
        if (message.command !== 'startHardwareSession' || !message.family) {
            return;
        }
        const selectedFamily = families.find((family) => family.family === message.family);
        if (!selectedFamily) {
            void vscode.window.showWarningMessage(`Unknown family from inventory panel: ${message.family}`);
            return;
        }
        try {
            await (0, settings_1.persistHardwareSessionDefaults)({
                processor: message.processor,
                scriptsPath: message.scriptsPath,
                toolScriptsPath: message.toolScriptsPath,
            });
            await (0, hardware_1.startHardwareSessionFlow)(backend, selectedFamily, {
                processor: message.processor,
                scriptsPath: message.scriptsPath,
                toolScriptsPath: message.toolScriptsPath,
            });
            await refreshViews?.();
        }
        catch (err) {
            const text = err instanceof Error ? err.message : String(err);
            backend.show();
            backend.log({ error: text, family: selectedFamily.family });
            void vscode.window.showErrorMessage(`Failed to start hardware session for ${selectedFamily.family}: ${text}`);
        }
    });
}
//# sourceMappingURL=familyInventoryPanel.js.map