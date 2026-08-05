@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements-dev.txt || exit /b 1
set QT_QPA_PLATFORM=offscreen
python -m pytest || exit /b 1
python -m PyInstaller --clean --noconfirm build.spec || exit /b 1

powershell -NoProfile -ExecutionPolicy Bypass -File ".\smoke_windows.ps1" || exit /b 1
echo Built dist\ChzzkClipMomentCatcher\ChzzkClipMomentCatcher.exe
