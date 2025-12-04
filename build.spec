# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Add src directory to path
src_path = str(Path('.').absolute() / 'src')

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'wordcloud',
        'PIL',
        'ui',
        'ui.main_window',
        'ui.styles',
        'core',
        'core.analyzer',
        'core.wordcloud_gen',
    ],
    hookspath=[],
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
    upx=True,
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
