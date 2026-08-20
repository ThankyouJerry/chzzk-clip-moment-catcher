#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 APP_BUNDLE [MAX_MACOS_VERSION]" >&2
  exit 2
fi

APP_BUNDLE="$1"
MAX_MACOS_VERSION="${2:-12.0}"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "App bundle not found: $APP_BUNDLE" >&2
  exit 2
fi

mach_o_count=0
violation_count=0
max_found=0

while IFS= read -r -d '' file_path; do
  file_info="$(file -b "$file_path")"
  case "$file_info" in
    *Mach-O*) ;;
    *) continue ;;
  esac

  mach_o_count=$((mach_o_count + 1))
  while IFS= read -r minos; do
    [[ -n "$minos" ]] || continue
    max_found="$(awk -v current="$max_found" -v candidate="$minos" \
      'BEGIN { print ((candidate + 0) > (current + 0)) ? candidate : current }')"
    if awk -v value="$minos" -v limit="$MAX_MACOS_VERSION" \
      'BEGIN { exit !((value + 0) > (limit + 0)) }'; then
      echo "Minimum macOS version exceeds $MAX_MACOS_VERSION: $file_path ($minos)" >&2
      violation_count=$((violation_count + 1))
    fi
  done < <(vtool -show-build "$file_path" 2>/dev/null | \
    awk '/^[[:space:]]*minos / {print $2}')
done < <(find "$APP_BUNDLE" -type f -print0)

if [[ "$mach_o_count" -eq 0 ]]; then
  echo "No Mach-O files found: $APP_BUNDLE" >&2
  exit 1
fi

if [[ "$violation_count" -ne 0 ]]; then
  echo "$violation_count incompatible Mach-O file(s) found." >&2
  exit 1
fi

echo "macOS compatibility verified: $mach_o_count Mach-O files, max minimum OS $max_found"
