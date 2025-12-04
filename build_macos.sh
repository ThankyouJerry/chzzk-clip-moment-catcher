#!/bin/bash

echo "Building Chzzk Chat Analyzer for macOS..."

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Build with PyInstaller
echo "Building application..."
pyinstaller build.spec

echo "Build complete! Application is in dist/ChzzkChatAnalyzer.app"
