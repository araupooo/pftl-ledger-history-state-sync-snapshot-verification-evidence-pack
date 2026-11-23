#!/bin/bash
# clean_reproduce.sh — full fresh-environment reproduction check.
#
# Copies the pack to a throwaway directory, drops all shipped probe /
# drill / analysis outputs and the generated manifest, re-runs every
# generation step from scratch, and compares the fresh numbers with the
# shipped ones via compare_reproduce.py. Exits 0 only if every comparison
# check passes.
#
# The fresh probe set is copied back into outputs/fresh-clone-* so the
# reproduction itself is evidence. Only read-only public probes run; no
# transactions, no votes, no live key material.
set -u
PACK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d /tmp/pftl-histsync-repro.XXXXXX)"
echo "clean_reproduce.sh workdir: $WORK"
cp -r "$PACK_ROOT" "$WORK/pack"
cd "$WORK/pack" || exit 1

# Save the shipped manifest for comparison, then drop everything the
# generation steps produce, so the run is from scratch.
cp run-manifest.json "$WORK/shipped-manifest.json"
rm -f outputs/*.json outputs/*.html outputs/*.log
rm -rf outputs/derived
mkdir -p outputs/derived
rm -f run-manifest.json
rm -f fixtures/source-hashes.json
rm -f fixtures/source-excerpts/*.txt

echo "--- step 1: probe (read-only) ---"
bash scripts/probe_all.sh || { echo "probe_all.sh FAILED"; exit 1; }
echo "--- step 2: analyze ---"
python3 scripts/analyze.py || { echo "analyze.py FAILED"; exit 1; }
echo "--- step 3: drill ---"
python3 scripts/drill.py || { echo "drill.py FAILED"; exit 1; }
echo "--- step 4: excerpts ---"
python3 scripts/extract_excerpts.py || { echo "extract_excerpts.py FAILED"; exit 1; }
echo "--- step 5: compare with shipped ---"
python3 scripts/compare_reproduce.py "$WORK/shipped-manifest.json" || { echo "compare_reproduce.py FAILED"; exit 1; }

echo "--- step 6: copy fresh outputs back as fresh-clone-* evidence ---"
for f in outputs/*.json outputs/*.html outputs/*.log; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  cp "$f" "$PACK_ROOT/outputs/fresh-clone-$base"
done
for f in outputs/derived/*; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  cp "$f" "$PACK_ROOT/outputs/fresh-clone-derived-$base"
done
# A short compare log for the submission note.
{
  echo "clean_reproduce.sh fresh run: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "workdir: $WORK"
  echo "shipped validated ledger: $(python3 -c "import json;print(json.load(open('$WORK/shipped-manifest.json'))['validated_ledger'])")"
  echo "fresh validated ledger: $(python3 -c "import json;print(json.load(open('run-manifest.json'))['validated_ledger'])")"
  echo "compare: $(python3 -c "import json;d=json.load(open('outputs/derived/compare-results.json'));print('%d/%d checks PASS' % (d['passed'], d['total']))")"
} > "$PACK_ROOT/outputs/fresh-clone-compare.log"
cat "$PACK_ROOT/outputs/fresh-clone-compare.log"
echo "clean_reproduce.sh: ALL CHECKS PASSED"
