#!/usr/bin/env bash
# Build the Phase-3 submission zip from COMMITTED files only (fully reproducible).
# Output: EIGENNEXUS_Challenge_Phase3.zip  (in the repo root)
#
# Note: the official GIC_2026 cover page must be prepended to PHASE3_PAPER.pdf as
# page 1 before final upload (see SUBMISSION_CHECKLIST.md) - it is not in the repo.
set -e
cd "$(dirname "$0")"
NAME="EIGENNEXUS_Challenge_Phase3"
OUT="${NAME}.zip"
rm -f "$OUT"
git archive --format=zip --prefix="${NAME}/" -o "$OUT" HEAD
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "contents:"
unzip -l "$OUT" | tail -n +4 | head -n 60
