from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


@dataclass(frozen=True)
class Segment:
    address: int
    data: bytes


@dataclass(frozen=True)
class FirmwareImage:
    """A simple memory image represented as absolute-addressed segments."""

    segments: Tuple[Segment, ...]
    entry_point: Optional[int] = None

    @property
    def min_address(self) -> int:
        return min((s.address for s in self.segments), default=0)

    @property
    def max_address(self) -> int:
        return max((s.address + len(s.data) for s in self.segments), default=0)

    def iter_bytes(self) -> Iterator[Tuple[int, int]]:
        for seg in self.segments:
            base = int(seg.address)
            for i, b in enumerate(seg.data):
                yield base + i, b

    def to_byte_dict(self) -> Dict[int, int]:
        return {addr: b for addr, b in self.iter_bytes()}

    def to_intel_hex_text(self, *, bytes_per_record: int = 16) -> str:
        if bytes_per_record <= 0 or bytes_per_record > 255:
            raise ValueError("bytes_per_record must be between 1 and 255")

        lines: List[str] = []
        upper = None

        for segment in self.segments:
            offset = 0
            while offset < len(segment.data):
                chunk = segment.data[offset : offset + bytes_per_record]
                address = segment.address + offset
                chunk_upper = (address >> 16) & 0xFFFF
                if upper != chunk_upper:
                    upper = chunk_upper
                    lines.append(_hex_record(0x0000, 0x04, bytes(((upper >> 8) & 0xFF, upper & 0xFF))))
                lines.append(_hex_record(address & 0xFFFF, 0x00, chunk))
                offset += len(chunk)

        lines.append(":00000001FF")
        return "\n".join(lines) + "\n"

    def to_intel_hex_path(self, path: str, *, bytes_per_record: int = 16) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.to_intel_hex_text(bytes_per_record=bytes_per_record))

    @classmethod
    def from_path(cls, path: str) -> "FirmwareImage":
        p = str(path)
        ext = os.path.splitext(p)[1].lower()
        if ext in {".hex", ".ihex"}:
            return cls.from_intel_hex_path(p)
        if ext == ".elf":
            return cls.from_elf_path(p)
        raise ValueError(f"Unsupported firmware format: {ext}")

    @classmethod
    def from_intel_hex_path(cls, path: str) -> "FirmwareImage":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return cls.from_intel_hex_text(text)

    @classmethod
    def from_intel_hex_text(cls, text: str) -> "FirmwareImage":
        """Parse Intel HEX (records 00/01/02/04).

        This is sufficient for typical Microchip toolchain HEX output.
        """

        upper = 0
        seg_upper = 0
        byte_map: Dict[int, int] = {}

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if not line.startswith(":"):
                continue

            rec = line[1:]
            if len(rec) < 10:
                raise ValueError(f"Invalid HEX record: {line}")

            count = int(rec[0:2], 16)
            addr = int(rec[2:6], 16)
            rectype = int(rec[6:8], 16)
            data_hex = rec[8:8 + count * 2]
            chk = int(rec[8 + count * 2: 8 + count * 2 + 2], 16)

            # Validate checksum (optional but cheap).
            total = count + ((addr >> 8) & 0xFF) + (addr & 0xFF) + rectype
            data_bytes: List[int] = []
            for i in range(0, len(data_hex), 2):
                b = int(data_hex[i:i + 2], 16)
                data_bytes.append(b)
                total += b
            total = (total + chk) & 0xFF
            if total != 0:
                raise ValueError(f"Bad HEX checksum: {line}")

            if rectype == 0x00:
                base = (upper << 16) + (seg_upper << 4) + addr
                for i, b in enumerate(data_bytes):
                    byte_map[base + i] = b
            elif rectype == 0x01:
                break
            elif rectype == 0x02:
                # Extended segment address
                if len(data_bytes) != 2:
                    raise ValueError(f"Invalid HEX type 02 record: {line}")
                seg_upper = (data_bytes[0] << 8) | data_bytes[1]
                upper = 0
            elif rectype == 0x04:
                # Extended linear address
                if len(data_bytes) != 2:
                    raise ValueError(f"Invalid HEX type 04 record: {line}")
                upper = (data_bytes[0] << 8) | data_bytes[1]
                seg_upper = 0
            else:
                # Ignore other record types for MVP.
                continue

        segments = _segments_from_byte_map(byte_map)
        return cls(segments=tuple(segments))

    @classmethod
    def from_elf_path(cls, path: str) -> "FirmwareImage":
        """Load loadable segments from ELF.

        Requires optional dependency: `pip install .[elf]`.
        """

        try:
            from elftools.elf.elffile import ELFFile  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("ELF support requires optional extra 'elf' (pyelftools)") from e

        segments: List[Segment] = []
        entry: Optional[int] = None

        with open(path, "rb") as f:
            elf = ELFFile(f)
            entry = int(elf.header.get("e_entry", 0))
            for seg in elf.iter_segments():
                p_type = seg.header.p_type
                if str(p_type) != "PT_LOAD":
                    continue
                addr = int(seg.header.p_paddr or seg.header.p_vaddr)
                data = seg.data()
                if data:
                    segments.append(Segment(address=addr, data=data))

        return cls(segments=tuple(segments), entry_point=entry)


def _segments_from_byte_map(byte_map: Dict[int, int]) -> List[Segment]:
    if not byte_map:
        return []

    addrs = sorted(byte_map.keys())
    segments: List[Segment] = []

    start = addrs[0]
    buf = bytearray([byte_map[start]])
    prev = start

    for a in addrs[1:]:
        if a == prev + 1:
            buf.append(byte_map[a])
        else:
            segments.append(Segment(address=start, data=bytes(buf)))
            start = a
            buf = bytearray([byte_map[a]])
        prev = a

    segments.append(Segment(address=start, data=bytes(buf)))
    return segments


def _hex_record(address: int, record_type: int, data: bytes) -> str:
    count = len(data)
    total = count + ((address >> 8) & 0xFF) + (address & 0xFF) + (record_type & 0xFF)
    total += sum(data)
    checksum = ((~total + 1) & 0xFF)
    return ":" + "".join(
        [
            f"{count:02X}",
            f"{address & 0xFFFF:04X}",
            f"{record_type & 0xFF:02X}",
            data.hex().upper(),
            f"{checksum:02X}",
        ]
    )
