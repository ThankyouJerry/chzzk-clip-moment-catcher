#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
  else
    PYTHON_BIN="python3"
  fi
fi
VENV_DIR="${VENV_DIR:-.build-venv}"
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Python 3.12 is required. Set PYTHON_BIN to a Python 3.12 executable.")'
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
