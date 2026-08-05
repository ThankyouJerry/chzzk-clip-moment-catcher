#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python3 -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python3 -m pytest
python3 -m PyInstaller --clean --noconfirm build.spec
./package_macos.sh \
  dist/ChzzkClipMomentCatcher.app \
  dist/ChzzkClipMomentCatcher-macOS-local.zip

echo "Built dist/ChzzkClipMomentCatcher-macOS-local.zip"
