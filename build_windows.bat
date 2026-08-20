@echo off
setlocal
cd /d "%~dp0"

if not defined PYTHON_BIN set "PYTHON_BIN=python"
if not defined VENV_DIR set "VENV_DIR=.build-venv"
%PYTHON_BIN% -m venv --clear "%VENV_DIR%" || exit /b 1
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip || exit /b 1
"%VENV_DIR%\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements-dev.txt || exit /b 1
"%VENV_DIR%\Scripts\python.exe" -m pip check || exit /b 1
"%VENV_DIR%\Scripts\python.exe" -m compileall -q src tests scripts || exit /b 1
"%VENV_DIR%\Scripts\python.exe" scripts\verify_release_version.py || exit /b 1
set QT_QPA_PLATFORM=offscreen
"%VENV_DIR%\Scripts\python.exe" -m pytest || exit /b 1
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --clean --noconfirm build.spec || exit /b 1
"%VENV_DIR%\Scripts\python.exe" scripts\verify_package_contents.py dist\ChzzkClipMomentCatcher || exit /b 1

powershell -NoProfile -ExecutionPolicy Bypass -File ".\smoke_windows.ps1" || exit /b 1
echo Built dist\ChzzkClipMomentCatcher\ChzzkClipMomentCatcher.exe
