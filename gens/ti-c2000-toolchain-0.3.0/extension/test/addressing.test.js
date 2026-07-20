const test = require('node:test');
const assert = require('node:assert/strict');
const { AddressTranslator } = require('../dist/c28x/addressing');

test('C28x word addresses map to byte addresses', () => {
  const translator = new AddressTranslator(2);
  assert.equal(translator.targetToByte(0x100n), 0x200n);
  assert.equal(translator.byteToTarget(0x200n), 0x100n);
  assert.throws(() => translator.byteToTarget(0x201n), /unaligned/);
});

test('unaligned byte windows are covered and sliced correctly', () => {
  const translator = new AddressTranslator(2);
  assert.deepEqual(translator.coveringTargetRange(3n, 4), {
    firstTarget: 1n,
    targetCount: 3,
    leadingBytes: 1,
    totalBytes: 6,
  });
  const bytes = translator.wordsToBytes([0x1122n, 0x3344n], 16);
  assert.deepEqual([...bytes], [0x22, 0x11, 0x44, 0x33]);
  assert.deepEqual(translator.bytesToWords(bytes, 16), [0x1122n, 0x3344n]);
});
