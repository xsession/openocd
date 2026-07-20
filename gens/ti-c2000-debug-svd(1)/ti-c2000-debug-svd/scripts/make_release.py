#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
dist.mkdir(exist_ok=True)
out = dist / "ti-c2000-debug-svd.zip"
exclude_parts = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "dist", "build", "node_modules"
}
with ZipFile(out, "w", ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_dir() or any(
            part in exclude_parts or part.endswith(".egg-info") for part in relative.parts
        ):
            continue
        archive.write(path, Path("ti-c2000-debug-svd") / relative)

digest = hashlib.sha256(out.read_bytes()).hexdigest()
checksum = out.with_suffix(out.suffix + ".sha256")
checksum.write_text(f"{digest}  {out.name}\n", encoding="ascii")
print(out)
print(checksum)
