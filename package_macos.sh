#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 SOURCE_APP OUTPUT_ZIP" >&2
  exit 2
fi

SOURCE_APP="$1"
OUTPUT_ZIP="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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
"$SCRIPT_DIR/scripts/verify_macos_compatibility.sh" "$STAGED_APP" 12.0

EXECUTABLE="$STAGED_APP/Contents/MacOS/ChzzkClipMomentCatcher"
if ! QT_QPA_PLATFORM=offscreen "$EXECUTABLE" --smoke-test >"$STAGE_DIR/functional-smoke.log" 2>&1; then
  cat "$STAGE_DIR/functional-smoke.log" >&2
  echo "Packaged app failed the functional smoke test." >&2
  exit 1
fi
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
rm -f "$OUTPUT_ZIP"
COPYFILE_DISABLE=1 ditto -c -k --norsrc --keepParent "$STAGED_APP" "$OUTPUT_ZIP"

archive_listing="$(unzip -Z1 "$OUTPUT_ZIP")"
if grep -Eq '(^|/)\._' <<< "$archive_listing"; then
  echo "AppleDouble metadata found in archive: $OUTPUT_ZIP" >&2
  exit 1
fi

EXTRACT_DIR="$STAGE_DIR/extracted"
mkdir -p "$EXTRACT_DIR"
ditto -x -k "$OUTPUT_ZIP" "$EXTRACT_DIR"
codesign --verify --deep --strict "$EXTRACT_DIR/$(basename "$SOURCE_APP")"
echo "Verified and archived: $OUTPUT_ZIP"
