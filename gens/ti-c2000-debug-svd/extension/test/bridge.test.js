const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const path = require('node:path');
const readline = require('node:readline');

test('CCS bridge protocol works with a fake scripting installation', async () => {
  const repo = path.resolve(__dirname, '../..');
  const bridge = path.join(repo, 'bridge/ccs-debug-bridge.js');
  const ccsRoot = path.resolve(__dirname, 'fixtures/fake-ccs');
  const child = childProcess.spawn(process.execPath, [bridge], { stdio: ['pipe', 'pipe', 'inherit'] });
  const lines = readline.createInterface({ input: child.stdout });
  let seq = 1;
  const pending = new Map();
  lines.on('line', (line) => {
    if (!line.startsWith('@@C2000@@')) return;
    const message = JSON.parse(line.slice('@@C2000@@'.length));
    if (message.id !== undefined && pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    }
  });
  const request = (method, params = {}) => new Promise((resolve, reject) => {
    const id = seq++;
    const timer = setTimeout(() => reject(new Error(`timeout ${method}`)), 3000);
    pending.set(id, (message) => {
      clearTimeout(timer);
      if (message.ok) resolve(message.result);
      else reject(new Error(message.error.message));
    });
    child.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
  });

  const initialized = await request('initialize', {
    ccsRoot,
    ccxml: '/tmp/fake.ccxml',
    device: 'tms320f28069',
    request: 'attach',
    addressScale: 2,
  });
  assert.equal(initialized.cores.length, 1);
  const registers = await request('registers', { coreId: 1 });
  assert.ok(registers.registers.some((register) => register.name === 'PC'));
  const memory = await request('readMemory', { coreId: 1, byteAddress: '2', byteCount: 4 });
  assert.deepEqual([...Buffer.from(memory.data, 'base64')], [1, 0, 2, 0]);
  const bp = await request('setBreakpoints', { coreId: 1, breakpoints: [{ source: 'main.c', line: 4 }] });
  assert.equal(bp.breakpoints[0].verified, true);
  await request('shutdown');
});
