export class AddressTranslator {
  public constructor(public readonly bytesPerAddressUnit: number) {
    if (!Number.isInteger(bytesPerAddressUnit) || bytesPerAddressUnit < 1) {
      throw new Error(`invalid address scale: ${bytesPerAddressUnit}`);
    }
  }

  public targetToByte(targetAddress: bigint): bigint {
    return targetAddress * BigInt(this.bytesPerAddressUnit);
  }

  public byteToTarget(byteAddress: bigint): bigint {
    const scale = BigInt(this.bytesPerAddressUnit);
    if (byteAddress % scale !== 0n) {
      throw new Error(
        `unaligned byte address 0x${byteAddress.toString(16)} for ${this.bytesPerAddressUnit}-byte target words`,
      );
    }
    return byteAddress / scale;
  }

  public coveringTargetRange(byteAddress: bigint, byteCount: number): {
    firstTarget: bigint;
    targetCount: number;
    leadingBytes: number;
    totalBytes: number;
  } {
    if (byteCount < 0) {
      throw new Error('byteCount must be non-negative');
    }
    const scale = BigInt(this.bytesPerAddressUnit);
    const firstTarget = byteAddress / scale;
    const leadingBytes = Number(byteAddress % scale);
    const total = leadingBytes + byteCount;
    const targetCount = Math.ceil(total / this.bytesPerAddressUnit);
    return {
      firstTarget,
      targetCount,
      leadingBytes,
      totalBytes: targetCount * this.bytesPerAddressUnit,
    };
  }

  public wordsToBytes(words: readonly bigint[], bitsPerWord = 16): Buffer {
    const bytesPerWord = bitsPerWord / 8;
    if (!Number.isInteger(bytesPerWord)) {
      throw new Error(`unsupported word size: ${bitsPerWord}`);
    }
    const output = Buffer.alloc(words.length * bytesPerWord);
    words.forEach((word, index) => {
      let value = word;
      for (let byte = 0; byte < bytesPerWord; byte += 1) {
        output[index * bytesPerWord + byte] = Number(value & 0xffn);
        value >>= 8n;
      }
    });
    return output;
  }

  public bytesToWords(data: Buffer, bitsPerWord = 16): bigint[] {
    const bytesPerWord = bitsPerWord / 8;
    if (data.length % bytesPerWord !== 0) {
      throw new Error(`data length ${data.length} is not aligned to ${bytesPerWord} bytes`);
    }
    const words: bigint[] = [];
    for (let offset = 0; offset < data.length; offset += bytesPerWord) {
      let value = 0n;
      for (let byte = bytesPerWord - 1; byte >= 0; byte -= 1) {
        value = (value << 8n) | BigInt(data[offset + byte]);
      }
      words.push(value);
    }
    return words;
  }
}
