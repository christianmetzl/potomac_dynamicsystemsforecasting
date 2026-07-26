#!/usr/bin/env bash
# Build the Phase-3 submission zip: COMMITTED files (fully reproducible) plus, when present
# locally, the cover-merged write-up EIGENNEXUS__Phase3_Version1.pdf, which is REQUIRED inside
# the upload zip by the GIC submission criteria but is deliberately NOT committed (it carries
# the official cover page with personal contact data; see SUBMISSION_CHECKLIST.md).
# Output: EIGENNEXUS_Challenge_Phase3.zip  (in the repo root)
set -e
cd "$(dirname "$0")"
NAME="EIGENNEXUS_Challenge_Phase3"
OUT="${NAME}.zip"
WRITEUP="EIGENNEXUS__Phase3_VersionDynamicSystemsForecastingTrackA.pdf"
rm -f "$OUT"
git archive --format=zip --prefix="${NAME}/" -o "$OUT" HEAD
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))  [from commit $(git rev-parse --short HEAD)]"

# Inject the cover-merged write-up (local-only file) so the UPLOAD zip is complete.
if [ -f "$WRITEUP" ]; then
  TMPD=$(mktemp -d)
  mkdir -p "$TMPD/$NAME"
  cp "$WRITEUP" "$TMPD/$NAME/"
  (cd "$TMPD" && zip -qX "$OLDPWD/$OUT" "$NAME/$WRITEUP")
  rm -rf "$TMPD"
  echo "injected $WRITEUP (cover-merged write-up; local-only, never committed)"
else
  echo "############################################################################"
  echo "# WARNING: $WRITEUP not found - the upload zip is INCOMPLETE."
  echo "# The GIC criteria require the write-up (with the official cover page as"
  echo "# page 1) INSIDE the zip. Build it per SUBMISSION_CHECKLIST.md first."
  echo "############################################################################"
fi

# zip freshness: warn if HEAD is not the latest v*-submission tag
LATEST_TAG=$(git tag -l 'v*-submission' | sort -V | tail -1)
if [ -n "$LATEST_TAG" ] && ! git diff --quiet "$LATEST_TAG" HEAD -- . 2>/dev/null; then
  echo "NOTE: HEAD differs from latest tag ${LATEST_TAG} - confirm this is intentional."
fi
echo ""
echo "upload checklist: cover's Aqora-Username cell filled -> repo public -> upload $OUT"
echo "contents (tail):"
unzip -l "$OUT" | tail -n 8
