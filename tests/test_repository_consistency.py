import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_application_version_has_one_source_of_truth():
    version_source = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
    main_source = (ROOT / "src" / "main.py").read_text(encoding="utf-8")
    spec_source = (ROOT / "build.spec").read_text(encoding="utf-8")

    assert 'APP_VERSION = "1.2.1"' in version_source
    assert "from version import APP_NAME, APP_VERSION" in main_source
    assert "from version import APP_VERSION, BUNDLE_IDENTIFIER" in spec_source
    assert 'setApplicationVersion("' not in main_source
    assert "## 1.2.1" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_only_one_entrypoint_and_one_pyinstaller_spec_exist():
    assert not (ROOT / "main.py").exists()
    assert [path.name for path in ROOT.glob("*.spec")] == ["build.spec"]


def test_ci_covers_qa_and_three_release_archives():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "macos-15-intel" in workflow
    assert "macos-14" in workflow
    assert "python -m pytest" in workflow
    assert "sudo apt-get install -y libegl1" in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "actions/download-artifact@v8" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "ChzzkClipMomentCatcher-Windows-x86_64.zip" in workflow
    assert "ChzzkClipMomentCatcher-macOS-x86_64.zip" in workflow
    assert "ChzzkClipMomentCatcher-macOS-arm64.zip" in workflow
    assert "contents: read" in workflow
    assert "./package_macos.sh" in workflow
    assert "./smoke_windows.ps1" in workflow


def test_macos_packaging_stages_before_signing_and_smoke_checks():
    script = (ROOT / "package_macos.sh").read_text(encoding="utf-8")

    assert "ditto --norsrc" in script
    assert "xattr -cr" in script
    assert "codesign --verify --deep --strict" in script
    assert "QT_QPA_PLATFORM=offscreen" in script


def test_windows_packaging_launches_the_built_executable():
    script = (ROOT / "smoke_windows.ps1").read_text(encoding="utf-8")

    assert "Start-Process" in script
    assert "Start-Sleep -Seconds 5" in script
    assert "Packaged app exited during smoke test" in script


def test_runtime_and_build_dependencies_are_separated():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").casefold()
    development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").casefold()

    assert "pyinstaller" not in runtime
    assert "pytest" not in runtime
    assert "pyinstaller" in development
    assert "pytest" in development
    assert "numpy==2.5.1" in runtime
    assert "pyinstaller==6.21.0" in development


def test_readme_documents_real_csv_schema_and_export_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "재생시간,닉네임,id,메시지" in readme
    assert "편집 작업표 CSV" in readme
    assert "Premiere 교환 XML" in readme
    assert "CSV를 사용할 수 있습니다" in readme
    assert "타임라인 우클릭" not in readme


def test_repository_text_does_not_contain_stale_local_identity():
    forbidden = ("h" + "vs", "jerry" + "mouse", "your_" + "username")
    ignored_dirs = {".git", ".pytest_cache", "__pycache__", "build", "dist", "venv", ".venv"}
    for directory, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [name for name in dirnames if name not in ignored_dirs]
        for filename in filenames:
            path = Path(directory) / filename
            if path.suffix.casefold() in {".csv", ".png", ".pyc"}:
                continue
            try:
                text = path.read_text(encoding="utf-8").casefold()
            except UnicodeDecodeError:
                continue
            assert not any(value in text for value in forbidden), path
