const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const net = require('node:net');
const path = require('node:path');

const REGISTER_NAMES = [
  'ACC', 'AH', 'AL', 'P', 'PH', 'PL', 'XT', 'T',
  'XAR0', 'XAR1', 'XAR2', 'XAR3', 'XAR4', 'XAR5', 'XAR6', 'XAR7',
  'AR0', 'AR1', 'AR2', 'AR3', 'AR4', 'AR5', 'AR6', 'AR7',
  'SP', 'PC', 'RPC', 'ST0', 'ST1', 'IFR', 'IER', 'DP',
];

class DapClient {
  constructor(program) {
    this.child = childProcess.spawn(process.execPath, [program], { stdio: ['pipe', 'pipe', 'pipe'] });
    this.seq = 1;
    this.buffer = Buffer.alloc(0);
    this.responses = new Map();
    this.events = [];
    this.waiters = [];
    this.child.stdout.on('data', (chunk) => this.handle(chunk));
    this.child.stderr.on('data', (chunk) => process.stderr.write(chunk));
  }
  request(command, args = {}) {
    const seq = this.seq++;
    const message = Buffer.from(JSON.stringify({ seq, type: 'request', command, arguments: args }));
    this.child.stdin.write(`Content-Length: ${message.length}\r\n\r\n`);
    this.child.stdin.write(message);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`timeout: ${command}`)), 3000);
      this.responses.set(seq, { resolve, reject, timer });
    });
  }
  waitEvent(name) {
    const existing = this.events.findIndex((event) => event.event === name);
    if (existing >= 0) return Promise.resolve(this.events.splice(existing, 1)[0]);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`event timeout: ${name}`)), 3000);
      this.waiters.push({ name, resolve, timer });
    });
  }
  handle(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (true) {
      const headerEnd = this.buffer.indexOf('\r\n\r\n');
      if (headerEnd < 0) return;
      const match = this.buffer.subarray(0, headerEnd).toString().match(/Content-Length:\s*(\d+)/i);
      if (!match) throw new Error('bad DAP header');
      const length = Number(match[1]);
      const start = headerEnd + 4;
      if (this.buffer.length < start + length) return;
      const message = JSON.parse(this.buffer.subarray(start, start + length).toString());
      this.buffer = this.buffer.subarray(start + length);
      if (message.type === 'response') {
        const pending = this.responses.get(message.request_seq);
        if (pending) {
          clearTimeout(pending.timer);
          this.responses.delete(message.request_seq);
          message.success ? pending.resolve(message) : pending.reject(new Error(message.message));
        }
      } else if (message.type === 'event') {
        const index = this.waiters.findIndex((waiter) => waiter.name === message.event);
        if (index >= 0) {
          const [waiter] = this.waiters.splice(index, 1);
          clearTimeout(waiter.timer);
          waiter.resolve(message);
        } else this.events.push(message);
      }
    }
  }
}

class FakeRenode {
  constructor() {
    this.halted = true;
    this.registers = new Map(REGISTER_NAMES.map((name, index) => [name, BigInt(index)]));
    this.registers.set('PC', 0x40n);
    this.server = net.createServer((socket) => {
      let input = '';
      socket.write('(monitor) ');
      socket.on('data', (chunk) => {
        input += chunk.toString().replace(/\r/g, '');
        let split;
        while ((split = input.indexOf('\n')) >= 0) {
          const command = input.slice(0, split).trim();
          input = input.slice(split + 1);
          if (!command) continue;
          const output = this.execute(command);
          socket.write(`${command}\r\n${output ? `${output}\r\n` : ''}(c2000-test) `);
        }
      });
    });
  }
  async start() {
    await new Promise((resolve) => this.server.listen(0, '127.0.0.1', resolve));
    return this.server.address().port;
  }
  async close() { await new Promise((resolve) => this.server.close(resolve)); }
  execute(command) {
    if (command === 'pause') { this.halted = true; return 'Pausing emulation...'; }
    if (command === 'start') {
      this.halted = false;
      setTimeout(() => { this.halted = true; }, 30);
      return 'Starting emulation...';
    }
    let match = command.match(/^cpu IsHalted(?: (true|false))?$/i);
    if (match) {
      if (match[1]) this.halted = match[1].toLowerCase() === 'true';
      return this.halted ? 'True' : 'False';
    }
    match = command.match(/^cpu GetRegister (\w+)$/i);
    if (match) return `0x${(this.registers.get(match[1].toUpperCase()) || 0n).toString(16)}`;
    match = command.match(/^sysbus ReadWord (0x[0-9a-f]+)$/i);
    if (match) return `0x${BigInt(match[1]).toString(16)}`;
    if (/^sysbus FindSymbolAt /.test(command)) return 'main';
    return '';
  }
}

test('DAP session launches the Renode backend', async () => {
  const fake = new FakeRenode();
  const port = await fake.start();
  const client = new DapClient(path.resolve(__dirname, '../dist/adapter.js'));
  await client.request('initialize', { adapterID: 'c2000-debug' });
  await client.waitEvent('initialized');
  await client.request('attach', {
    backend: 'renode',
    device: 'tms320f28069',
    renodeLaunch: false,
    renodeHost: '127.0.0.1',
    renodeMonitorPort: port,
    renodeStopPollIntervalMs: 10,
    addressScale: 2,
  });
  await client.waitEvent('process');
  const threads = await client.request('threads');
  assert.equal(threads.body.threads.length, 1);
  const threadId = threads.body.threads[0].id;
  const stack = await client.request('stackTrace', { threadId });
  assert.equal(stack.body.stackFrames[0].name, 'main');
  const frameId = stack.body.stackFrames[0].id;
  const scopes = await client.request('scopes', { frameId });
  const variables = await client.request('variables', { variablesReference: scopes.body.scopes[0].variablesReference });
  assert.equal(variables.body.variables.length, 32);
  const memory = await client.request('readMemory', { threadId, memoryReference: '0x2', count: 4 });
  assert.deepEqual([...Buffer.from(memory.body.data, 'base64')], [1, 0, 2, 0]);
  const continued = client.waitEvent('continued');
  const stopped = client.waitEvent('stopped');
  await client.request('continue', { threadId });
  await continued;
  await stopped;
  await client.request('disconnect', { terminateDebuggee: false });
  await fake.close();
});
