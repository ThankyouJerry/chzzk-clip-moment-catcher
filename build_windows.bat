@echo off

echo Building Chzzk Chat Analyzer for Windows...

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Build with PyInstaller
echo Building application...
pyinstaller build.spec

echo Build complete! Application is in dist\ChzzkChatAnalyzer\ChzzkChatAnalyzer.exe
