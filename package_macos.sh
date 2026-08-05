#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 SOURCE_APP OUTPUT_ZIP" >&2
  exit 2
fi

SOURCE_APP="$1"
OUTPUT_ZIP="$2"

if [[ ! -d "$SOURCE_APP" ]]; then
  echo "App bundle not found: $SOURCE_APP" >&2
  exit 1
fi

STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/clip-moment-package.XXXXXX")"
STAGED_APP="$STAGE_DIR/$(basename "$SOURCE_APP")"

cleanup() {
  rm -rf "$STAGE_DIR"
}
trap cleanup EXIT

# Cloud-backed folders can attach Finder metadata that invalidates code signing.
ditto --norsrc "$SOURCE_APP" "$STAGED_APP"
xattr -cr "$STAGED_APP"
codesign --force --deep --sign - "$STAGED_APP"
codesign --verify --deep --strict "$STAGED_APP"

EXECUTABLE="$STAGED_APP/Contents/MacOS/ChzzkClipMomentCatcher"
QT_QPA_PLATFORM=offscreen "$EXECUTABLE" >"$STAGE_DIR/smoke.log" 2>&1 &
APP_PID=$!
sleep 5
if ! kill -0 "$APP_PID" 2>/dev/null; then
  wait "$APP_PID" || true
  cat "$STAGE_DIR/smoke.log" >&2
  echo "Packaged app exited during smoke test." >&2
  exit 1
fi
kill "$APP_PID"
wait "$APP_PID" 2>/dev/null || true

mkdir -p "$(dirname "$OUTPUT_ZIP")"
ditto -c -k --keepParent "$STAGED_APP" "$OUTPUT_ZIP"
echo "Verified and archived: $OUTPUT_ZIP"
