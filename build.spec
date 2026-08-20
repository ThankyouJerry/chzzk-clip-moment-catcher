# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path, PurePosixPath
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


ROOT = Path(SPECPATH).resolve()
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from version import APP_VERSION, BUNDLE_IDENTIFIER

datas = collect_data_files("wordcloud", includes=["stopwords"])
binaries = collect_dynamic_libs("wordcloud") + collect_dynamic_libs("PIL")
hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "matplotlib.backends.backend_qtagg",
    "ui.main_window",
    "ui.styles",
    "core.analyzer",
    "core.errors",
    "core.file_io",
    "core.sentiment_analyzer",
    "core.timeline",
    "core.wordcloud_gen",
]

analysis = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

forbidden_data_parts = {"__pycache__", "examples", "sample_data", "test", "tests"}
forbidden_data_suffixes = {".py", ".pyc", ".pyo"}


def is_runtime_data(entry):
    destination = PurePosixPath(str(entry[0]).replace("\\", "/"))
    parts = {part.casefold() for part in destination.parts}
    return not (
        parts & forbidden_data_parts
        or destination.suffix.casefold() in forbidden_data_suffixes
    )


analysis.datas = [entry for entry in analysis.datas if is_runtime_data(entry)]
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
