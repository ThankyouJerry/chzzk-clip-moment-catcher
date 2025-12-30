# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Add src directory to path
src_path = str(Path('.').absolute() / 'src')

block_cipher = None

# Collect all matplotlib data and submodules
matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all('matplotlib')
pillow_datas, pillow_binaries, pillow_hiddenimports = collect_all('PIL')
wordcloud_datas, wordcloud_binaries, wordcloud_hiddenimports = collect_all('wordcloud')

a = Analysis(
    ['src/main.py'],
    pathex=[src_path],
    binaries=matplotlib_binaries + pillow_binaries + wordcloud_binaries,
    datas=matplotlib_datas + pillow_datas + wordcloud_datas + [
        ('src/ui', 'ui'),
        ('src/core', 'core'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.figure',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_qt5agg',
        'wordcloud',
        'PIL',
        'PIL.Image',
        'ui',
        'ui.main_window',
        'ui.styles',
        'core',
        'core.analyzer',
        'core.wordcloud_gen',
        'core.sentiment_analyzer',
    ] + matplotlib_hiddenimports + pillow_hiddenimports + wordcloud_hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ChzzkClipMomentCatcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChzzkClipMomentCatcher',
)

app = BUNDLE(
    coll,
    name='ChzzkClipMomentCatcher.app',
    icon=None,
    bundle_identifier='com.chzzkclipmomentcatcher.app',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
    },
)
