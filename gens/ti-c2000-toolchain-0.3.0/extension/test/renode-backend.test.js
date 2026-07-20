const test = require('node:test');
const assert = require('node:assert/strict');
const net = require('node:net');
const { RenodeBackend } = require('../dist/backends/renodeBackend');

const REGISTER_NAMES = [
  'ACC', 'AH', 'AL', 'P', 'PH', 'PL', 'XT', 'T',
  'XAR0', 'XAR1', 'XAR2', 'XAR3', 'XAR4', 'XAR5', 'XAR6', 'XAR7',
  'AR0', 'AR1', 'AR2', 'AR3', 'AR4', 'AR5', 'AR6', 'AR7',
  'SP', 'PC', 'RPC', 'ST0', 'ST1', 'IFR', 'IER', 'DP',
];

class FakeRenodeMonitor {
  constructor() {
    this.server = net.createServer((socket) => this.accept(socket));
    this.registers = new Map(REGISTER_NAMES.map((name, index) => [name, BigInt(index)]));
    this.registers.set('PC', 0x10n);
    this.memory = new Map([[1n, 0x1122n], [2n, 0x3344n], [3n, 0x5566n]]);
    this.halted = true;
    this.hooks = [];
  }

  async start() {
    await new Promise((resolve) => this.server.listen(0, '127.0.0.1', resolve));
    return this.server.address().port;
  }

  async close() {
    await new Promise((resolve) => this.server.close(resolve));
  }

  accept(socket) {
    let buffer = '';
    let machineSelected = false;
    socket.write('(monitor) ');
    socket.on('data', (chunk) => {
      buffer += chunk.toString().replace(/\r/g, '');
      let newline;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const command = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (!command) continue;
        const output = this.command(command);
        if (command.startsWith('include ')) machineSelected = true;
        socket.write(`${command}\r\n${output ? `${output}\r\n` : ''}${machineSelected ? '(c2000-test) ' : '(monitor) '}`);
      }
    });
  }

  command(command) {
    if (command === 'pause') {
      this.halted = true;
      return 'Pausing emulation...';
    }
    if (command === 'start') {
      this.halted = false;
      setTimeout(() => { this.halted = true; }, 35);
      return 'Starting emulation...';
    }
    let match = command.match(/^cpu IsHalted(?: (true|false))?$/i);
    if (match) {
      if (match[1]) this.halted = match[1].toLowerCase() === 'true';
      return this.halted ? 'True' : 'False';
    }
    match = command.match(/^cpu GetRegister (\w+)$/i);
    if (match) return `0x${(this.registers.get(match[1].toUpperCase()) ?? 0n).toString(16)}`;
    match = command.match(/^cpu SetRegister (\d+) (0x[0-9a-f]+)$/i);
    if (match) {
      this.registers.set(REGISTER_NAMES[Number(match[1])], BigInt(match[2]));
      return '';
    }
    match = command.match(/^sysbus ReadWord (0x[0-9a-f]+)$/i);
    if (match) return `0x${(this.memory.get(BigInt(match[1])) ?? 0n).toString(16)}`;
    match = command.match(/^sysbus WriteWord (0x[0-9a-f]+) (0x[0-9a-f]+)$/i);
    if (match) {
      this.memory.set(BigInt(match[1]), BigInt(match[2]));
      return '';
    }
    if (/^cpu ExecutionMode /.test(command)) return '';
    if (command === 'cpu Step') {
      this.registers.set('PC', (this.registers.get('PC') ?? 0n) + 1n);
      return '';
    }
    if (/^sysbus FindSymbolAt /.test(command)) return 'main';
    match = command.match(/^cpu AddHook (0x[0-9a-f]+)/i);
    if (match) {
      this.hooks.push(BigInt(match[1]));
      return '';
    }
    match = command.match(/^cpu RemoveHooksAt (0x[0-9a-f]+)/i);
    if (match) {
      this.hooks = this.hooks.filter((item) => item !== BigInt(match[1]));
      return '';
    }
    if (command === 'machine Reset') {
      this.registers.set('PC', 0n);
      return '';
    }
    if (command.startsWith('include ')) return 'Including script(s): fake.resc';
    return '';
  }
}

test('Renode backend matches xsession custom C2000 monitor semantics', async () => {
  const fake = new FakeRenodeMonitor();
  const port = await fake.start();
  const backend = new RenodeBackend();
  const events = [];
  backend.onEvent((event) => events.push(event));

  const cores = await backend.start({
    backend: 'renode',
    request: 'attach',
    device: 'tms320f28069',
    addressScale: 2,
    renodeHost: '127.0.0.1',
    renodeMonitorPort: port,
    renodeLaunch: false,
    renodeStopPollIntervalMs: 10,
  });
  assert.equal(cores.length, 1);
  assert.equal(cores[0].architecture, 'c28x');

  const registers = await backend.registers(1);
  assert.equal(registers.length, 32);
  assert.equal(registers.find((register) => register.name === 'PC').value, 0x10n);
  assert.equal(registers.find((register) => register.name === 'AH').bits, 16);

  await backend.writeRegister(1, 'ACC', 0x12345678n);
  assert.equal(await backend.evaluate(1, 'ACC'), '0x12345678');

  const memory = await backend.readMemory(1, 3n, 4);
  assert.deepEqual([...memory], [0x11, 0x44, 0x33, 0x66]);
  await backend.writeMemory(1, 3n, Buffer.from([0xaa, 0xbb, 0xcc]));
  assert.equal(fake.memory.get(1n), 0xaa22n);
  assert.equal(fake.memory.get(2n), 0xccbbn);

  const bp = await backend.setBreakpoints(1, [{ address: 0x20n }, { source: 'main.c', line: 7 }]);
  assert.equal(bp[0].verified, true);
  assert.equal(bp[1].verified, false);
  assert.deepEqual(fake.hooks, [0x20n]);

  const beforePc = fake.registers.get('PC');
  await backend.step(1, 'instruction');
  assert.equal(fake.registers.get('PC'), beforePc + 1n);

  await backend.continue(1);
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.ok(events.some((event) => event.event === 'continued'));
  assert.ok(events.some((event) => event.event === 'stopped' && event.reason === 'breakpoint'));

  await backend.reset(1);
  assert.equal(fake.registers.get('PC'), 0n);
  await backend.stop(false);
  await fake.close();
});
