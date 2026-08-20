#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.build-venv}"
"$PYTHON_BIN" -m venv --clear "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install --only-binary=:all: -r requirements-dev.txt
"$VENV_DIR/bin/python" -m pip check
"$VENV_DIR/bin/python" -m compileall -q src tests scripts
"$VENV_DIR/bin/python" scripts/verify_release_version.py
QT_QPA_PLATFORM=offscreen "$VENV_DIR/bin/python" -m pytest
"$VENV_DIR/bin/python" -m PyInstaller --clean --noconfirm build.spec
"$VENV_DIR/bin/python" scripts/verify_package_contents.py dist/ChzzkClipMomentCatcher.app
./package_macos.sh \
  dist/ChzzkClipMomentCatcher.app \
  dist/ChzzkClipMomentCatcher-macOS-local.zip

echo "Built dist/ChzzkClipMomentCatcher-macOS-local.zip"
