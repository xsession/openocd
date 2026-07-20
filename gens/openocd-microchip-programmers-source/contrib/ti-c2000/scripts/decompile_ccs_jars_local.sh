#!/usr/bin/env sh
set -eu
if [ $# -lt 3 ]; then
  echo "usage: $0 /path/to/ccs_base /path/to/cfr.jar|none /output/dir" >&2
  exit 2
fi
CCS="$1"
CFR="$2"
OUT="$3"
mkdir -p "$OUT/classes" "$OUT/javap" "$OUT/decompiled"
find "$CCS" -type f -name '*.jar' | sort > "$OUT/jars.txt"
while IFS= read -r jar; do
  base=$(basename "$jar")
  jar tf "$jar" | sort > "$OUT/classes/$base.classes.txt"
  unzip -p "$jar" META-INF/MANIFEST.MF > "$OUT/classes/$base.MANIFEST.MF.txt" 2>/dev/null || true
  if [ "$CFR" != "none" ] && [ -f "$CFR" ]; then
    mkdir -p "$OUT/decompiled/$base"
    java -jar "$CFR" "$jar" --outputdir "$OUT/decompiled/$base" >/dev/null
  fi
  # Bytecode/signature summaries for TI classes only.
  jar tf "$jar" | grep '^com/ti/.*\.class$' | sed 's#/#.#g;s#\.class$##' | while IFS= read -r cls; do
    safe=$(echo "$cls" | tr '.#$' '___')
    javap -classpath "$jar" -c -p "$cls" > "$OUT/javap/$safe.txt" 2>/dev/null || true
  done
done < "$OUT/jars.txt"
