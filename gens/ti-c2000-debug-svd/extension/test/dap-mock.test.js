const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const path = require('node:path');

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
      const header = this.buffer.subarray(0, headerEnd).toString();
      const match = header.match(/Content-Length:\s*(\d+)/i);
      if (!match) throw new Error(`bad header: ${header}`);
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
          if (message.success) pending.resolve(message);
          else pending.reject(new Error(message.message));
        }
      } else if (message.type === 'event') {
        const waiterIndex = this.waiters.findIndex((waiter) => waiter.name === message.event);
        if (waiterIndex >= 0) {
          const [waiter] = this.waiters.splice(waiterIndex, 1);
          clearTimeout(waiter.timer);
          waiter.resolve(message);
        } else {
          this.events.push(message);
        }
      }
    }
  }
}

test('mock backend completes a representative DAP session', async () => {
  const client = new DapClient(path.resolve(__dirname, '../dist/adapter.js'));
  await client.request('initialize', { adapterID: 'c2000-debug' });
  await client.waitEvent('initialized');
  await client.request('launch', {
    backend: 'mock',
    device: 'tms320f28069',
    addressScale: 2,
    executable: '/tmp/app.out',
  });
  await client.waitEvent('process');

  const threads = await client.request('threads');
  assert.equal(threads.body.threads.length, 1);
  const threadId = threads.body.threads[0].id;

  const stack = await client.request('stackTrace', { threadId });
  assert.equal(stack.body.stackFrames.length, 1);
  const frameId = stack.body.stackFrames[0].id;

  const scopes = await client.request('scopes', { frameId });
  const reference = scopes.body.scopes[0].variablesReference;
  const variables = await client.request('variables', { variablesReference: reference });
  assert.ok(variables.body.variables.some((variable) => variable.name === 'PC'));

  const read = await client.request('readMemory', { memoryReference: '0x10', count: 4, threadId });
  assert.deepEqual([...Buffer.from(read.body.data, 'base64')], [0x10, 0x11, 0x12, 0x13]);
  await client.request('writeMemory', {
    memoryReference: '0x10',
    data: Buffer.from([1, 2, 3, 4]).toString('base64'),
    threadId,
  });
  const reread = await client.request('readMemory', { memoryReference: '0x10', count: 4, threadId });
  assert.deepEqual([...Buffer.from(reread.body.data, 'base64')], [1, 2, 3, 4]);

  const evaluated = await client.request('evaluate', { expression: 'PC', frameId });
  assert.match(evaluated.body.result, /^0x/);

  const continued = client.waitEvent('continued');
  const stopped = client.waitEvent('stopped');
  await client.request('continue', { threadId });
  await continued;
  await stopped;

  await client.request('disconnect', { terminateDebuggee: true });
});
