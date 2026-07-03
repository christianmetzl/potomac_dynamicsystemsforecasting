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
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))  [from commit $(git rev-parse --short HEAD)]"
# zip freshness: warn if HEAD is not the latest v*-submission tag
LATEST_TAG=$(git tag -l 'v*-submission' | sort -V | tail -1)
if [ -n "$LATEST_TAG" ] && ! git diff --quiet "$LATEST_TAG" HEAD -- . 2>/dev/null; then
  echo "NOTE: HEAD differs from latest tag ${LATEST_TAG} - confirm this is intentional."
fi
echo ""
echo "############################################################################"
echo "# REQUIRED MANUAL STEP BEFORE UPLOAD (see SUBMISSION_CHECKLIST.md):"
echo "#   1. Prepend the OFFICIAL GIC_2026 cover page (from Aqora) as page 1 of"
echo "#      PHASE3_PAPER.pdf - it may NOT be recreated or modified."
echo "#   2. Re-verify the merged PDF: body must remain EXACTLY 5 pages"
echo "#      (cover-page merge via Word/LibreOffice can reflow text)."
echo "############################################################################"
echo "contents:"
unzip -l "$OUT" | tail -n +4 | head -n 60
