# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


ROOT = Path(SPECPATH).resolve()
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from version import APP_VERSION, BUNDLE_IDENTIFIER

datas = collect_data_files("matplotlib") + collect_data_files("wordcloud")
binaries = collect_dynamic_libs("wordcloud") + collect_dynamic_libs("PIL")
hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "matplotlib.backends.backend_qtagg",
    "ui.main_window",
    "ui.styles",
    "core.analyzer",
    "core.sentiment_analyzer",
    "core.wordcloud_gen",
]

analysis = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ChzzkClipMomentCatcher",
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

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="ChzzkClipMomentCatcher",
)

app = BUNDLE(
    collection,
    name="ChzzkClipMomentCatcher.app",
    bundle_identifier=BUNDLE_IDENTIFIER,
    info_plist={
        "CFBundleDisplayName": "Chzzk Clip Moment Catcher",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
)
