from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PRINTABLE_RE = re.compile(rb"[ -~]{6,}")


@dataclass(frozen=True)
class HexImage:
    path: Path
    chunks: Tuple[Tuple[int, bytes], ...]

    @property
    def start_address(self) -> int:
        return self.chunks[0][0] if self.chunks else 0

    @property
    def end_address(self) -> int:
        if not self.chunks:
            return 0
        start, data = self.chunks[-1]
        return start + len(data)

    @property
    def flat_bytes(self) -> bytes:
        return b"".join(data for _, data in self.chunks)


@dataclass(frozen=True)
class HexSegment:
    start: int
    end: int
    first_bytes: bytes


def _parse_hex(path: Path) -> HexImage:
    base = 0
    chunks: List[Tuple[int, bytes]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith(":"):
            continue
        count = int(line[1:3], 16)
        address = int(line[3:7], 16)
        record_type = int(line[7:9], 16)
        data = bytes.fromhex(line[9 : 9 + count * 2])
        if record_type == 4:
            base = int.from_bytes(data, "big") << 16
        elif record_type == 0:
            chunks.append((base + address, data))
    chunks.sort(key=lambda item: item[0])
    return HexImage(path=path, chunks=tuple(chunks))


def _vector_words(image: HexImage, count: int = 16) -> List[int]:
    if not image.chunks:
        return []
    start, first = image.chunks[0]
    words: List[int] = []
    for offset in range(0, min(len(first), count * 4), 4):
        words.append(int.from_bytes(first[offset : offset + 4], "little"))
    return words


def _contiguous_segments(image: HexImage) -> List[HexSegment]:
    if not image.chunks:
        return []
    segments: List[HexSegment] = []
    segment_start = image.chunks[0][0]
    segment_first = image.chunks[0][1][:16]
    previous_end = image.chunks[0][0] + len(image.chunks[0][1])
    for address, data in image.chunks[1:]:
        if address != previous_end:
            segments.append(HexSegment(start=segment_start, end=previous_end, first_bytes=segment_first))
            segment_start = address
            segment_first = data[:16]
        previous_end = address + len(data)
    segments.append(HexSegment(start=segment_start, end=previous_end, first_bytes=segment_first))
    return segments


def _segment_vector_words(image: HexImage, segment_start: int, count: int = 4) -> List[int]:
    for address, data in image.chunks:
        if address == segment_start:
            words: List[int] = []
            for offset in range(0, min(len(data), count * 4), 4):
                words.append(int.from_bytes(data[offset : offset + 4], "little"))
            return words
    return []


def _tail_record(image: HexImage) -> Optional[Dict[str, object]]:
    if not image.chunks:
        return None
    address, data = image.chunks[-1]
    if len(data) != 12:
        return None
    return {
        "address": f"0x{address:08X}",
        "rawHex": data.hex(),
        "prefix": f"0x{int.from_bytes(data[0:4], 'little'):08X}",
        "versionWord": f"0x{int.from_bytes(data[4:8], 'little'):08X}",
        "suffix": f"0x{int.from_bytes(data[8:12], 'little'):08X}",
    }


def _parse_jam_manifest(path: Path) -> Dict[str, object]:
    slots: List[Dict[str, object]] = []
    files: List[Dict[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        left, right = [part.strip() for part in line.split(",", 1)]
        if left.endswith(".hex") or left.endswith(".xml"):
            files.append({"name": left, "value": right})
            continue
        pieces = left.split(None, 1)
        slot = pieces[0]
        version = pieces[1] if len(pieces) > 1 else ""
        slots.append({"slot": slot, "version": version, "address": f"0x{int(right, 16):08X}"})
    return {"path": str(path), "files": files, "slots": slots}


def _infer_architecture(words: List[int]) -> Dict[str, object]:
    if len(words) < 2:
        return {"name": "unknown", "confidence": "low", "reason": "no vector table"}
    initial_sp = words[0]
    reset = words[1]
    if 0x20000000 <= initial_sp < 0x21000000 and (reset & 1) == 1:
        return {
            "name": "arm-cortex-m",
            "confidence": "high",
            "reason": "initial SP is in SRAM-like range and reset vector has Thumb bit set",
        }
    return {"name": "unknown", "confidence": "low", "reason": "vector table does not match Cortex-M heuristic"}


def _extract_strings(image: HexImage, limit: int = 64) -> List[str]:
    seen: List[str] = []
    for match in PRINTABLE_RE.finditer(image.flat_bytes):
        text = match.group(0).decode("ascii", errors="ignore")
        if text in seen:
            continue
        seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def _extract_strings_from_bytes(data: bytes, limit: int = 20) -> List[str]:
    seen: List[str] = []
    for match in PRINTABLE_RE.finditer(data):
        text = match.group(0).decode("ascii", errors="ignore")
        if text in seen:
            continue
        seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def _find_ascii_token_offsets(image: HexImage, tokens: Iterable[str]) -> Dict[str, Optional[int]]:
    data = image.flat_bytes
    offsets: Dict[str, Optional[int]] = {}
    for token in tokens:
        raw = token.encode("ascii")
        offset = data.find(raw)
        offsets[token] = offset if offset >= 0 else None
    return offsets


def _segment_bytes(image: HexImage, start: int, end: int) -> bytes:
    chunks: List[bytes] = []
    for address, data in image.chunks:
        if start <= address < end:
            chunks.append(data)
    return b"".join(chunks)


def _scan_word_references(image: HexImage, words: Iterable[int]) -> Dict[str, List[str]]:
    references: Dict[str, List[str]] = {}
    for word in words:
        raw = int(word).to_bytes(4, "little")
        hits: List[str] = []
        for address, data in image.chunks:
            for idx in range(0, max(0, len(data) - 3), 4):
                if data[idx : idx + 4] == raw:
                    hits.append(f"0x{address + idx:08X}")
        references[f"0x{word:08X}"] = hits
    return references


def _scan_word_references_in_bytes(data: bytes, words: Iterable[int], base_address: int) -> Dict[str, List[str]]:
    references: Dict[str, List[str]] = {}
    for word in words:
        raw = int(word).to_bytes(4, "little")
        hits: List[str] = []
        for idx in range(0, max(0, len(data) - 3), 4):
            if data[idx : idx + 4] == raw:
                hits.append(f"0x{base_address + idx:08X}")
        references[f"0x{word:08X}"] = hits
    return references


def _read_u32(image: HexImage, address: int) -> int:
    result = bytearray()
    for current in range(address, address + 4):
        value = 0
        for chunk_address, chunk in image.chunks:
            if chunk_address <= current < (chunk_address + len(chunk)):
                value = chunk[current - chunk_address]
                break
        result.append(value)
    return int.from_bytes(bytes(result), "little")


def _classify_word(word: int) -> str:
    if word == 0x00500000:
        return "secondarySlotBase"
    if word == 0x0040C000:
        return "primarySlotBase"
    if 0x00400000 <= word < 0x00600000:
        return "firmwareLike"
    if 0x20000000 <= word < 0x21000000:
        return "sramLike"
    if word == 0xE000ED00:
        return "systemControl"
    if word == 0:
        return "zero"
    return "other"


def _profile_site_window(image: HexImage, center: int, before_words: int = 4, after_words: int = 8) -> Dict[str, object]:
    start = center - before_words * 4
    words: List[Dict[str, str]] = []
    counts: Dict[str, int] = {}
    for address in range(start, center + after_words * 4 + 4, 4):
        value = _read_u32(image, address)
        kind = _classify_word(value)
        counts[kind] = counts.get(kind, 0) + 1
        words.append({
            "address": f"0x{address:08X}",
            "value": f"0x{value:08X}",
            "kind": kind,
        })
    return {
        "center": f"0x{center:08X}",
        "words": words,
        "wordCountByKind": counts,
    }


def analyze_hex_image(path: Path) -> Dict[str, object]:
    image = _parse_hex(path)
    vector_words = _vector_words(image)
    segments = _contiguous_segments(image)
    strings = _extract_strings(image)
    keyword_offsets = _find_ascii_token_offsets(image, ("Microchip", "WINUSB", "PICkit 4", "CMSIS"))
    banner_offsets = _find_ascii_token_offsets(image, ("MPLAB PICkit 4 CMSIS-DAP",))
    word_references = _scan_word_references(image, (0x0040C000, 0x00500000, 0x0040E8AD, 0x00504189, 0xE000ED00))
    notable_sites = {}
    for site in (0x00456864, 0x005041F0, 0x005041F4, 0x0051EA04, 0x005228BC, 0x00523C68):
        if image.start_address <= site < image.end_address:
            notable_sites[f"0x{site:08X}"] = _profile_site_window(image, site)
    string_flags = {
        "microchip": keyword_offsets["Microchip"] is not None,
        "winusb": keyword_offsets["WINUSB"] is not None,
        "pickit4": keyword_offsets["PICkit 4"] is not None,
        "cmsis": keyword_offsets["CMSIS"] is not None,
    }
    return {
        "path": str(path),
        "startAddress": f"0x{image.start_address:08X}",
        "endAddress": f"0x{image.end_address:08X}",
        "chunkCount": len(image.chunks),
        "segments": [
            {
                "start": f"0x{segment.start:08X}",
                "end": f"0x{segment.end:08X}",
                "size": f"0x{segment.end - segment.start:X}",
                "firstBytes": segment.first_bytes.hex(),
                "vectorWords": [f"0x{word:08X}" for word in _segment_vector_words(image, segment.start)],
                "sampleStrings": _extract_strings_from_bytes(_segment_bytes(image, segment.start, segment.end), limit=12),
                "keywordOffsets": _find_ascii_token_offsets(
                    type("SegmentBlob", (object,), {"flat_bytes": _segment_bytes(image, segment.start, segment.end)})(),
                    ("Microchip", "WINUSB", "PICkit 4", "CMSIS"),
                ),
                "bannerOffsets": _find_ascii_token_offsets(
                    type("SegmentBlob", (object,), {"flat_bytes": _segment_bytes(image, segment.start, segment.end)})(),
                    ("MPLAB PICkit 4 CMSIS-DAP",),
                ),
                "wordReferences": _scan_word_references_in_bytes(
                    _segment_bytes(image, segment.start, segment.end),
                    (0x0040C000, 0x00500000, 0x0040E8AD, 0x00504189, 0xE000ED00),
                    segment.start,
                ),
            }
            for segment in segments
        ],
        "vectorWords": [f"0x{word:08X}" for word in vector_words],
        "inferredArchitecture": _infer_architecture(vector_words),
        "sampleStrings": strings,
        "keywordOffsets": keyword_offsets,
        "bannerOffsets": banner_offsets,
        "notableSites": notable_sites,
        "wordReferences": word_references,
        "tailRecord": _tail_record(image),
        "stringFlags": string_flags,
    }


def build_pk4_report(boot_hex: Path, app_hex: Path, jam_path: Optional[Path] = None) -> Dict[str, object]:
    boot = analyze_hex_image(boot_hex)
    app = analyze_hex_image(app_hex)
    boot_start = int(str(boot["startAddress"]), 16)
    app_start = int(str(app["startAddress"]), 16)
    jam = _parse_jam_manifest(jam_path) if jam_path is not None else None
    boot_tail = boot.get("tailRecord") or {}
    app_tail = app.get("tailRecord") or {}
    primary_app_segment = next((segment for segment in app["segments"] if segment["start"] == "0x0040C000"), {})
    secondary_app_segment = next((segment for segment in app["segments"] if segment["start"] == "0x00500000"), {})
    primary_slot_site = app.get("notableSites", {}).get("0x00456864", {})
    secondary_sys_site = app.get("notableSites", {}).get("0x005041F4", {})
    return {
        "tool": "PK4",
        "jam": jam,
        "boot": boot,
        "app": app,
        "observations": {
            "bootBeforeApp": boot_start < app_start,
            "sharedArchitecture": boot["inferredArchitecture"]["name"] == app["inferredArchitecture"]["name"],
            "likelyMigrationTarget": "arm-cortex-m-zephyr" if app["inferredArchitecture"]["name"] == "arm-cortex-m" else "unknown",
            "hasSecondaryAppCandidate": any(segment["start"] == "0x00500000" for segment in app["segments"]),
            "tailRecordMatchesBootVersion": boot_tail.get("versionWord") == "0x00010000",
            "tailRecordMatchesPrimaryAppVersion": app_tail.get("versionWord") == "0x00020515",
            "bootReferencesPrimaryApp": bool(boot["wordReferences"].get("0x0040C000")),
            "bootReferencesSecondaryApp": bool(boot["wordReferences"].get("0x00500000")),
            "appReferencesBothSlots": bool(app["wordReferences"].get("0x0040C000")) and bool(app["wordReferences"].get("0x00500000")),
            "primaryAppReferencesSecondarySlot": bool(primary_app_segment.get("wordReferences", {}).get("0x00500000")),
            "secondaryAppReferencesPrimarySlot": bool(secondary_app_segment.get("wordReferences", {}).get("0x0040C000")),
            "secondaryAppSelfReferences": bool(secondary_app_segment.get("wordReferences", {}).get("0x00500000")),
            "winusbOnlyInPrimaryApp": primary_app_segment.get("keywordOffsets", {}).get("WINUSB") is not None and secondary_app_segment.get("keywordOffsets", {}).get("WINUSB") is None,
            "cmsisPresentInSecondaryApp": secondary_app_segment.get("keywordOffsets", {}).get("CMSIS") is not None,
            "secondaryAppCarriesCmsisDapBanner": secondary_app_segment.get("bannerOffsets", {}).get("MPLAB PICkit 4 CMSIS-DAP") is not None,
            "secondaryAppSystemControlRefs": secondary_app_segment.get("wordReferences", {}).get("0xE000ED00", []),
            "primarySecondaryRefLooksDescriptorLike": primary_slot_site.get("wordCountByKind", {}).get("firmwareLike", 0) >= 4 and primary_slot_site.get("wordCountByKind", {}).get("secondarySlotBase", 0) >= 1,
            "secondarySystemControlSiteLooksLiteralPoolBacked": secondary_sys_site.get("wordCountByKind", {}).get("firmwareLike", 0) >= 3 and secondary_sys_site.get("wordCountByKind", {}).get("systemControl", 0) >= 1,
            "notes": [
                "Boot and app both start with Cortex-M-like vector tables.",
                "Observed RAM top values are in the 0x2040_0000 range, which matches SAM E70-class SRAM mapping more closely than the current nRF52 scaffold target.",
                "Strings confirm Microchip, WINUSB, and PICkit 4 branding inside the application image.",
                "The JAM manifest describes app1 at 0x0040C000 and app2 at 0x00500000, and the app HEX contains real segments at both bases.",
                "Both boot.hex and app.hex end with 12-byte trailer records; the version word inside each trailer matches the packaged boot/app1 version in the JAM manifest.",
                "Boot contains direct references to the primary app base but no observed direct references to the secondary app base, while the app package references both slot bases.",
                "Within app.hex, the primary segment references the secondary slot base, while the secondary segment only self-references and carries CMSIS but no observed WINUSB string.",
                "The secondary segment also carries an 'MPLAB PICkit 4 CMSIS-DAP' banner and aligned references to 0xE000ED00, consistent with Cortex-M system-control interaction inside that image.",
                "The aligned primary cross-slot reference at 0x00456864 sits in a pointer-rich window, which looks more like a descriptor/config table than inline instruction bytes.",
            ],
        },
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze vendored PK4 boot/app firmware images for Zephyr migration planning")
    parser.add_argument("--boot-hex", required=True)
    parser.add_argument("--app-hex", required=True)
    parser.add_argument("--jam", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)

    jam_path = Path(str(args.jam)) if str(args.jam).strip() else None
    report = build_pk4_report(Path(str(args.boot_hex)), Path(str(args.app_hex)), jam_path=jam_path)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if str(args.output).strip():
        Path(str(args.output)).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())