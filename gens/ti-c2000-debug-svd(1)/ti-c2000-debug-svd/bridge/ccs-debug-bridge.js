#!/usr/bin/env node
'use strict';

const path = require('node:path');
const readline = require('node:readline');

const MARKER = '@@C2000@@';
let ds = null;
let pollTimer = null;
const cores = new Map();

function wireValue(value) {
  if (typeof value === 'bigint') {
    return value.toString();
  }
  if (Array.isArray(value)) {
    return value.map(wireValue);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, wireValue(child)]));
  }
  return value;
}

function send(message) {
  process.stdout.write(`${MARKER}${JSON.stringify(wireValue(message))}\n`);
}

function respond(id, result) {
  send({ id, ok: true, result });
}

function reject(id, error) {
  send({
    id,
    ok: false,
    error: {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    },
  });
}

function event(name, body = {}) {
  send({ event: name, ...body });
}

function c28xBaseRegisters() {
  return [
    ['ACC', 32, 'Core'], ['P', 32, 'Core'], ['XT', 32, 'Core'],
    ...Array.from({ length: 8 }, (_, i) => [`XAR${i}`, 32, 'Address']),
    ['SP', 16, 'Address'], ['DP', 16, 'Address'],
    ['IFR', 16, 'Status'], ['IER', 16, 'Status'], ['DBGIER', 16, 'Status'],
    ['ST0', 16, 'Status'], ['ST1', 16, 'Status'],
    ['PC', 32, 'Control'], ['RPC', 32, 'Control'], ['RB', 32, 'Control'], ['RAS', 32, 'Control'],
  ];
}

function registerProfile(device, architecture, override = 'auto') {
  if (architecture === 'cortex-m3' || override === 'cortex-m3') {
    return [
      ...Array.from({ length: 13 }, (_, i) => [`R${i}`, 32, 'Core']),
      ['SP', 32, 'Core'], ['LR', 32, 'Core'], ['PC', 32, 'Core'], ['XPSR', 32, 'Status'],
      ['MSP', 32, 'Special'], ['PSP', 32, 'Special'], ['PRIMASK', 32, 'Special'],
      ['BASEPRI', 32, 'Special'], ['FAULTMASK', 32, 'Special'], ['CONTROL', 32, 'Special'],
    ];
  }
  const base = c28xBaseRegisters();
  if (override === 'c28x') return base;
  const fpu = [...Array.from({ length: 8 }, (_, i) => [`R${i}H`, 32, 'FPU']), ['STF', 32, 'FPU']];
  const vcu = [['VCRC', 32, 'VCU'], ['VSTATUS', 32, 'VCU']];
  const tmu = [['TMU_STATUS', 32, 'TMU']];
  if (override === 'c28x-fpu-vcu') return [...base, ...fpu, ...vcu];
  if (override === 'c28x-fpu-tmu-vcu') return [...base, ...fpu, ...tmu, ...vcu];
  const normalized = String(device).toLowerCase();
  if (normalized.includes('280049')) return [...base, ...fpu, ...tmu, ...vcu];
  if (normalized.includes('28069')) return [...base, ...fpu, ...vcu];
  if (normalized.includes('28m35')) return [...base, ...fpu];
  return base;
}

function parseCoreDefinitions(params, configuredCores) {
  if (Array.isArray(params.cores) && params.cores.length) {
    return params.cores;
  }
  let architecture = String(params.device).endsWith('_m3') ? 'cortex-m3' : 'c28x';
  let pattern = params.corePattern;
  if (!pattern) {
    pattern = architecture === 'cortex-m3' ? 'Cortex_M3|CortexM3|M3' : 'C28xx|C28x';
  }
  return [{
    name: params.device,
    pattern,
    architecture,
    device: params.device,
    executable: params.executable,
    loadProgram: params.request !== 'attach',
    addressScale: params.addressScale ?? (architecture === 'c28x' ? 2 : 1),
  }];
}

function loadScripting(ccsRoot) {
  if (typeof globalThis.initScripting === 'function') {
    return globalThis.initScripting;
  }
  if (!ccsRoot) {
    throw new Error('CCS root is missing and initScripting is not available globally');
  }
  const modulePath = path.join(ccsRoot, 'ccs', 'scripting', 'node_modules', 'scripting');
  return require(modulePath).initScripting;
}

function ensureCore(coreId) {
  const core = cores.get(Number(coreId));
  if (!core) {
    throw new Error(`unknown core ${coreId}`);
  }
  return core;
}

function targetAddress(core, byteAddress) {
  const scale = BigInt(core.addressScale);
  const address = BigInt(byteAddress);
  if (address % scale !== 0n) {
    throw new Error(`unaligned instruction address 0x${address.toString(16)} for scale ${core.addressScale}`);
  }
  return address / scale;
}

function bytesFromWords(words, bytesPerWord) {
  const output = Buffer.alloc(words.length * bytesPerWord);
  words.forEach((word, index) => {
    let value = BigInt(word);
    for (let byte = 0; byte < bytesPerWord; byte += 1) {
      output[index * bytesPerWord + byte] = Number(value & 0xffn);
      value >>= 8n;
    }
  });
  return output;
}

function wordsFromBytes(data, bytesPerWord) {
  const words = [];
  for (let offset = 0; offset < data.length; offset += bytesPerWord) {
    let value = 0n;
    for (let byte = bytesPerWord - 1; byte >= 0; byte -= 1) {
      value = (value << 8n) | BigInt(data[offset + byte]);
    }
    words.push(value);
  }
  return words;
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(() => {
    for (const core of cores.values()) {
      try {
        const halted = core.session.target.isHalted();
        core.halted = halted;
        if (core.running && halted) {
          core.running = false;
          event('stopped', { coreId: core.id, reason: 'breakpoint' });
        }
      } catch (error) {
        event('output', { text: `CCS state polling failed for ${core.name}: ${error.message}\n` });
      }
    }
  }, 100);
}

const handlers = {
  initialize(params) {
    if (!params.ccxml) throw new Error('ccxml is required');
    const ccsRoot = params.ccsRoot || process.env.C2000_CCS_ROOT;
    const initScripting = loadScripting(ccsRoot);
    ds = initScripting();
    if (typeof ds.setScriptingTimeout === 'function') ds.setScriptingTimeout(0);
    const configured = ds.configure(params.ccxml);
    const definitions = parseCoreDefinitions(params, configured.cores || []);
    let coreId = 1;
    for (const definition of definitions) {
      const session = ds.openSession(definition.pattern);
      if (!session.target.isConnected()) session.target.connect();
      if (params.resetOnLaunch) {
        session.target.halt();
        session.target.reset();
        session.target.halt();
      }
      const executable = definition.executable || params.executable;
      const shouldLoad = definition.loadProgram !== false && params.request !== 'attach';
      if (shouldLoad && executable) {
        session.memory.loadProgram(executable);
        if (params.verifyProgram) session.memory.verifyProgram(executable);
      }
      const architecture = definition.architecture || (String(definition.device || params.device).endsWith('_m3') ? 'cortex-m3' : 'c28x');
      const core = {
        id: coreId++,
        name: definition.name || session.getName(),
        session,
        architecture,
        device: definition.device || params.device,
        addressScale: Number(definition.addressScale || (architecture === 'c28x' ? 2 : 1)),
        registerProfile: params.registerProfile || 'auto',
        breakpoints: [],
        running: false,
        halted: session.target.isHalted(),
      };
      cores.set(core.id, core);

      if (params.runToEntryPoint && params.request !== 'attach' && session.target.isHalted()) {
        const bp = session.breakpoints.add(params.runToEntryPoint);
        try {
          session.target.run(true);
        } finally {
          session.breakpoints.remove(bp);
        }
      }
    }
    startPolling();
    return { cores: [...cores.values()].map(({ session, breakpoints, running, ...core }) => core) };
  },

  threads() {
    for (const core of cores.values()) {
      core.halted = core.session.target.isHalted();
    }
    return { cores: [...cores.values()].map(({ session, breakpoints, running, ...core }) => core) };
  },

  continue({ coreId }) {
    const core = ensureCore(coreId);
    core.session.target.run(false);
    core.running = true;
    core.halted = false;
    event('continued', { coreId: core.id });
    return {};
  },

  halt({ coreId }) {
    const core = ensureCore(coreId);
    core.session.target.halt();
    core.running = false;
    core.halted = true;
    event('stopped', { coreId: core.id, reason: 'pause' });
    return {};
  },

  step({ coreId, kind }) {
    const core = ensureCore(coreId);
    if (kind === 'over') core.session.target.stepOver();
    else if (kind === 'out') core.session.target.stepOut();
    else if (kind === 'instruction') core.session.target.stepInto(true);
    else core.session.target.stepInto();
    event('stopped', { coreId: core.id, reason: 'step' });
    return {};
  },

  reset({ coreId }) {
    const core = ensureCore(coreId);
    core.session.target.halt();
    core.session.target.reset();
    core.session.target.halt();
    core.running = false;
    core.halted = true;
    event('stopped', { coreId: core.id, reason: 'restart' });
    return {};
  },

  registers({ coreId }) {
    const core = ensureCore(coreId);
    const registers = [];
    for (const [name, bits, group] of registerProfile(core.device, core.architecture, core.registerProfile)) {
      try {
        registers.push({ name, value: core.session.registers.read(name), bits, group });
      } catch (error) {
        // Register availability varies by silicon revision and target XML. Omit unsupported names.
      }
    }
    return { registers };
  },

  writeRegister({ coreId, name, value }) {
    ensureCore(coreId).session.registers.write(name, BigInt(value));
    return {};
  },

  evaluate({ coreId, expression }) {
    const value = ensureCore(coreId).session.expressions.evaluate(expression);
    return { value: value === undefined ? '<void>' : String(value) };
  },

  stack({ coreId }) {
    const core = ensureCore(coreId);
    const pc = core.session.registers.read('PC');
    let name = '<unknown>';
    try {
      const symbols = core.session.symbols.lookupSymbols(pc);
      if (symbols.length) name = symbols[0];
    } catch {}
    return { frames: [{ id: core.id * 1000 + 1, name, pc }] };
  },

  readMemory({ coreId, byteAddress, byteCount }) {
    const core = ensureCore(coreId);
    const address = BigInt(byteAddress);
    const scale = core.addressScale;
    const firstTarget = address / BigInt(scale);
    const leading = Number(address % BigInt(scale));
    const targetCount = Math.ceil((leading + Number(byteCount)) / scale);
    const bitSize = scale * 8;
    const words = core.session.memory.read(firstTarget, targetCount, bitSize);
    const data = bytesFromWords(words, scale).subarray(leading, leading + Number(byteCount));
    return { data: data.toString('base64') };
  },

  writeMemory({ coreId, byteAddress, data }) {
    const core = ensureCore(coreId);
    const incoming = Buffer.from(data, 'base64');
    const address = BigInt(byteAddress);
    const scale = core.addressScale;
    const firstTarget = address / BigInt(scale);
    const leading = Number(address % BigInt(scale));
    const targetCount = Math.ceil((leading + incoming.length) / scale);
    const bitSize = scale * 8;
    let bytes;
    if (leading === 0 && incoming.length % scale === 0) {
      bytes = incoming;
    } else {
      const existing = core.session.memory.read(firstTarget, targetCount, bitSize);
      bytes = bytesFromWords(existing, scale);
      incoming.copy(bytes, leading);
    }
    core.session.memory.write(firstTarget, wordsFromBytes(bytes, scale), bitSize);
    return { bytesWritten: incoming.length };
  },

  setBreakpoints({ coreId, breakpoints }) {
    const core = ensureCore(coreId);
    for (const id of core.breakpoints) {
      try { core.session.breakpoints.remove(id); } catch {}
    }
    core.breakpoints = [];
    const results = [];
    for (let index = 0; index < breakpoints.length; index += 1) {
      const breakpoint = breakpoints[index];
      try {
        let id;
        if (breakpoint.source && breakpoint.line) {
          id = core.session.breakpoints.add(breakpoint.source, Number(breakpoint.line));
        } else if (breakpoint.expression) {
          id = core.session.breakpoints.add(breakpoint.expression);
        } else if (breakpoint.address !== undefined) {
          id = core.session.breakpoints.add(targetAddress(core, breakpoint.address));
        } else {
          throw new Error('breakpoint has no location');
        }
        core.breakpoints.push(id);
        results.push({ id, verified: true, line: breakpoint.line });
      } catch (error) {
        results.push({ id: index + 1, verified: false, line: breakpoint.line, message: error.message });
      }
    }
    return { breakpoints: results };
  },

  disconnect() {
    for (const core of cores.values()) {
      try {
        if (core.session.target.isConnected()) core.session.target.disconnect();
      } catch {}
    }
    return {};
  },

  shutdown() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    try {
      for (const core of cores.values()) {
        if (core.session.target.isConnected()) core.session.target.disconnect();
      }
    } catch {}
    cores.clear();
    if (ds) {
      ds.shutdown();
      ds = null;
    }
    setTimeout(() => process.exit(0), 10);
    return {};
  },
};

const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on('line', async (line) => {
  if (!line.trim()) return;
  let request;
  try {
    request = JSON.parse(line);
    const handler = handlers[request.method];
    if (!handler) throw new Error(`unknown bridge method: ${request.method}`);
    const result = await handler(request.params || {});
    respond(request.id, result);
  } catch (error) {
    reject(request && request.id, error);
  }
});

process.on('uncaughtException', (error) => {
  event('output', { text: `CCS bridge uncaught exception: ${error.stack || error.message}\n` });
});
process.on('unhandledRejection', (error) => {
  event('output', { text: `CCS bridge unhandled rejection: ${error && error.stack ? error.stack : error}\n` });
});
