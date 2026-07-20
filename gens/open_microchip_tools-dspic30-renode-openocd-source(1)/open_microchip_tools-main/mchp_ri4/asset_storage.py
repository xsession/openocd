from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, TextIO, Tuple

from .repo_assets import vendor_root


_XMLISH_SUFFIXES = (".xml", ".pic")


def _iter_xmlish_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lower_name = path.name.lower()
        if lower_name.endswith(".xml") or lower_name.endswith(".pic"):
            yield path
            continue
        if lower_name.endswith(".xml.gz") or lower_name.endswith(".pic.gz"):
            yield path


def _logical_xmlish_path(path: Path) -> Path:
    if path.suffix.lower() != ".gz":
        return path
    return path.with_suffix("")


def _open_xmlish_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rb") as handle:
            return handle.read()
    return path.read_bytes()


def _collect_namespace_prefixes(data: bytes) -> Dict[str, str]:
    uri_to_prefix: Dict[str, str] = {}
    used_prefixes: Dict[str, str] = {}
    generated_index = 0

    for _, ns_tuple in ET.iterparse(io.BytesIO(data), events=("start-ns",)):
        prefix, uri = ns_tuple
        if uri in uri_to_prefix:
            continue
        candidate = (prefix or "ns").strip() or "ns"
        while candidate in used_prefixes and used_prefixes[candidate] != uri:
            generated_index += 1
            candidate = f"ns{generated_index}"
        uri_to_prefix[uri] = candidate
        used_prefixes[candidate] = uri
    return uri_to_prefix


def _qualify_xml_name(name: str, uri_to_prefix: Dict[str, str]) -> str:
    if not name.startswith("{"):
        return name
    uri, local = name[1:].split("}", 1)
    prefix = uri_to_prefix.get(uri)
    if not prefix:
        return local
    return f"{prefix}:{local}"


def _yaml_scalar(value: object) -> str:
    text = str(value)
    needs_quotes = (
        text == ""
        or text != text.strip()
        or any(ch in text for ch in [":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", ">", "!", "%", "@", "`", "\n", "\r", "\t"])
        or text.lower() in {"null", "true", "false", "yes", "no", "on", "off"}
    )
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"' if needs_quotes else escaped


def _write_yaml_line(handle: TextIO, indent: int, text: str) -> None:
    handle.write("  " * indent)
    handle.write(text)
    handle.write("\n")


def _group_children(children: List[ET.Element], uri_to_prefix: Dict[str, str]) -> List[Tuple[str, List[ET.Element]]]:
    grouped: Dict[str, List[ET.Element]] = {}
    ordered_names: List[str] = []
    for child in children:
        qualified_name = _qualify_xml_name(child.tag, uri_to_prefix)
        grouped.setdefault(qualified_name, []).append(child)
        if qualified_name not in ordered_names:
            ordered_names.append(qualified_name)
    return [(name, grouped[name]) for name in ordered_names]


def _write_element_body(handle: TextIO, elem: ET.Element, uri_to_prefix: Dict[str, str], indent: int) -> bool:
    wrote_any = False
    if elem.attrib:
        wrote_any = True
        _write_yaml_line(handle, indent, "attributes:")
        for attr_name, attr_value in elem.attrib.items():
            qualified_attr = _qualify_xml_name(attr_name, uri_to_prefix)
            _write_yaml_line(handle, indent + 1, f"{_yaml_scalar(qualified_attr)}: {_yaml_scalar(attr_value)}")

    text = (elem.text or "").strip()
    if text:
        wrote_any = True
        _write_yaml_line(handle, indent, f"text: {_yaml_scalar(text)}")

    children = list(elem)
    if children:
        wrote_any = True
        _write_yaml_line(handle, indent, "children:")
        for child_name, child_group in _group_children(children, uri_to_prefix):
            if len(child_group) == 1:
                child = child_group[0]
                if _write_inline_empty_element(handle, child_name, child, uri_to_prefix, indent + 1):
                    continue
                _write_yaml_line(handle, indent + 1, f"{_yaml_scalar(child_name)}:")
                _write_element_body(handle, child, uri_to_prefix, indent + 2)
                continue

            _write_yaml_line(handle, indent + 1, f"{_yaml_scalar(child_name)}:")
            for child in child_group:
                if _element_is_empty(child):
                    _write_yaml_line(handle, indent + 2, "- {}")
                    continue
                _write_yaml_line(handle, indent + 2, "-")
                _write_element_body(handle, child, uri_to_prefix, indent + 3)
    return wrote_any


def _element_is_empty(elem: ET.Element) -> bool:
    return not elem.attrib and not list(elem) and not (elem.text or "").strip()


def _write_inline_empty_element(
    handle: TextIO,
    name: str,
    elem: ET.Element,
    uri_to_prefix: Dict[str, str],
    indent: int,
) -> bool:
    if not _element_is_empty(elem):
        return False
    _write_yaml_line(handle, indent, f"{_yaml_scalar(name)}: {{}}")
    return True


def export_yaml_file(source_path: Path, destination_path: Path) -> None:
    data = _open_xmlish_bytes(source_path)
    uri_to_prefix = _collect_namespace_prefixes(data)
    root = ET.fromstring(data)

    with destination_path.open("w", encoding="utf-8") as handle:
        if uri_to_prefix:
            _write_yaml_line(handle, 0, "namespaces:")
            for uri, prefix in sorted(uri_to_prefix.items(), key=lambda item: item[1]):
                _write_yaml_line(handle, 1, f"{_yaml_scalar(prefix)}: {_yaml_scalar(uri)}")
        _write_yaml_line(handle, 0, "document:")
        root_name = _qualify_xml_name(root.tag, uri_to_prefix)
        if _write_inline_empty_element(handle, root_name, root, uri_to_prefix, 1):
            return
        _write_yaml_line(handle, 1, f"{_yaml_scalar(root_name)}:")
        _write_element_body(handle, root, uri_to_prefix, 2)


def export_yaml_gzip_file(source_path: Path, destination_path: Path) -> None:
    data = _open_xmlish_bytes(source_path)
    uri_to_prefix = _collect_namespace_prefixes(data)
    root = ET.fromstring(data)

    with gzip.open(destination_path, "wt", encoding="utf-8") as handle:
        if uri_to_prefix:
            _write_yaml_line(handle, 0, "namespaces:")
            for uri, prefix in sorted(uri_to_prefix.items(), key=lambda item: item[1]):
                _write_yaml_line(handle, 1, f"{_yaml_scalar(prefix)}: {_yaml_scalar(uri)}")
        _write_yaml_line(handle, 0, "document:")
        root_name = _qualify_xml_name(root.tag, uri_to_prefix)
        if _write_inline_empty_element(handle, root_name, root, uri_to_prefix, 1):
            return
        _write_yaml_line(handle, 1, f"{_yaml_scalar(root_name)}:")
        _write_element_body(handle, root, uri_to_prefix, 2)


def export_yaml_tree(source_root: Path, destination_root: Path, *, gzip_output: bool = False) -> Dict[str, object]:
    exported: List[str] = []
    for source_path in sorted(_iter_xmlish_files(source_root)):
        logical_path = _logical_xmlish_path(source_path)
        relative_path = logical_path.relative_to(source_root)
        yaml_relative_path = relative_path.with_suffix(".yaml")
        destination_path = destination_root / yaml_relative_path
        if gzip_output:
            destination_path = destination_path.with_suffix(destination_path.suffix + ".gz")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if gzip_output:
                export_yaml_gzip_file(source_path, destination_path)
            else:
                export_yaml_file(source_path, destination_path)
        except Exception:
            if destination_path.exists():
                destination_path.unlink()
            raise
        exported.append(str(destination_path))
    return {
        "sourceRoot": str(source_root),
        "destinationRoot": str(destination_root),
        "exportedCount": len(exported),
        "exportedFiles": exported,
        "gzipOutput": gzip_output,
    }


def create_tar_xz_archive(source_root: Path, archive_path: Path) -> Dict[str, object]:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:xz") as archive:
        archive.add(source_root, arcname=source_root.name)
    return {
        "sourceRoot": str(source_root),
        "archivePath": str(archive_path),
        "archiveBytes": archive_path.stat().st_size,
    }


def read_yaml_lines(path: Path, *, start_line: int = 1, end_line: Optional[int] = None) -> Dict[str, object]:
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if end_line is not None and end_line < start_line:
        raise ValueError("end_line must be >= start_line")

    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    else:
        lines = path.read_text(encoding="utf-8").splitlines()

    selected = lines[start_line - 1 : end_line]
    return {
        "path": str(path),
        "startLine": start_line,
        "endLine": start_line + len(selected) - 1 if selected else start_line - 1,
        "lineCount": len(selected),
        "text": "\n".join(selected),
    }


def build_storage_report(source_root: Path) -> Dict[str, object]:
    xmlish_files = sorted(_iter_xmlish_files(source_root))
    raw_files = [path for path in xmlish_files if path.suffix.lower() != ".gz"]
    compressed_files = [path for path in xmlish_files if path.suffix.lower() == ".gz"]

    hash_groups: Dict[str, List[Path]] = {}
    for path in compressed_files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hash_groups.setdefault(digest, []).append(path)
    duplicate_groups = [paths for paths in hash_groups.values() if len(paths) > 1]
    duplicate_groups.sort(key=len, reverse=True)

    return {
        "sourceRoot": str(source_root),
        "xmlishFileCount": len(xmlish_files),
        "rawXmlishCount": len(raw_files),
        "rawXmlishBytes": sum(path.stat().st_size for path in raw_files),
        "compressedXmlishCount": len(compressed_files),
        "compressedXmlishBytes": sum(path.stat().st_size for path in compressed_files),
        "duplicateCompressedGroupCount": len(duplicate_groups),
        "duplicateCompressedBytesReclaimable": sum(sum(path.stat().st_size for path in paths[1:]) for paths in duplicate_groups),
        "largestCompressedFiles": [
            {"path": str(path), "bytes": path.stat().st_size}
            for path in sorted(compressed_files, key=lambda item: item.stat().st_size, reverse=True)[:10]
        ],
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Report and export storage-friendly views of vendored MPLAB XML assets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Summarize XML/PIC storage in a vendor tree")
    report_parser.add_argument("--source-root", default=str(vendor_root()))

    export_parser = subparsers.add_parser("export-yaml", help="Export vendored XML/PIC assets as YAML for inspection")
    export_parser.add_argument("--source-root", default=str(vendor_root()))
    export_parser.add_argument("--output-root", required=True)
    export_parser.add_argument("--gzip", action="store_true", help="Write .yaml.gz files instead of plain .yaml")

    view_parser = subparsers.add_parser("view-yaml", help="Print lines from an exported .yaml or .yaml.gz file")
    view_parser.add_argument("path")
    view_parser.add_argument("--start-line", type=int, default=1)
    view_parser.add_argument("--end-line", type=int)

    archive_parser = subparsers.add_parser("archive-xz", help="Create a tar.xz archive of a vendor tree")
    archive_parser.add_argument("--source-root", default=str(vendor_root()))
    archive_parser.add_argument("--output", required=True)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "report":
        result = build_storage_report(Path(str(args.source_root)))
    elif args.command == "export-yaml":
        result = export_yaml_tree(Path(str(args.source_root)), Path(str(args.output_root)), gzip_output=bool(args.gzip))
    elif args.command == "view-yaml":
        result = read_yaml_lines(Path(str(args.path)), start_line=int(args.start_line), end_line=int(args.end_line) if args.end_line is not None else None)
    else:
        result = create_tar_xz_archive(Path(str(args.source_root)), Path(str(args.output)))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())