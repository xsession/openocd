#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="ascii").strip()
metadata = json.loads((root / "extension/package.json").read_text(encoding="utf-8"))
if metadata["version"] != version:
    raise SystemExit(
        f"version mismatch: VERSION={version}, extension={metadata['version']}"
    )

vsix = root / "extension" / f"c2000-debug-{version}.vsix"
if not vsix.is_file():
    raise SystemExit(f"missing {vsix}; run make extension-package first")

dist = root / "dist"
dist.mkdir(exist_ok=True)
out = dist / f"ti-c2000-toolchain-{version}.zip"
archive_root = Path(f"ti-c2000-toolchain-{version}")
exclude_parts = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "node_modules",
}

with ZipFile(out, "w", ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_dir() or any(
            part in exclude_parts or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        archive.write(path, archive_root / relative)

digest = hashlib.sha256(out.read_bytes()).hexdigest()
checksum = out.with_suffix(out.suffix + ".sha256")
checksum.write_text(f"{digest}  {out.name}\n", encoding="ascii")

vsix_digest = hashlib.sha256(vsix.read_bytes()).hexdigest()
checksums = dist / "SHA256SUMS"
checksums.write_text(
    f"{digest}  {out.name}\n{vsix_digest}  ../extension/{vsix.name}\n",
    encoding="ascii",
)

print(out)
print(checksum)
print(checksums)
