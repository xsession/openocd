#!/usr/bin/env sh
set -eu
if [ $# -lt 2 ]; then
  echo "usage: $0 /path/to/ccs_base /output/dir" >&2
  exit 2
fi
CCS="$1"
OUT="$2"
mkdir -p "$OUT"
find "$CCS" -type f \( -name '*.dll' -o -name '*.dvr' -o -name '*.so' \) | sort > "$OUT/native-files.txt"
while IFS= read -r f; do
  base=$(basename "$f")
  objdump -p "$f" > "$OUT/$base.objdump-p.txt" 2>/dev/null || true
  objdump -d "$f" > "$OUT/$base.objdump-d.txt" 2>/dev/null || true
  strings -a "$f" | sort -u > "$OUT/$base.strings.txt" || true
  strings -a "$f" | grep -Ei 'c28x|c2000|gti_|trg_|xds|memread|memwrite|readreg|writereg|halt|run|step|icepick|prsc|smg' | sort -u > "$OUT/$base.filtered-strings.txt" || true
done < "$OUT/native-files.txt"
