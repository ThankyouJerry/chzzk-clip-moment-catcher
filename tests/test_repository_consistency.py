import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_application_version_has_one_source_of_truth():
    version_source = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
    main_source = (ROOT / "src" / "main.py").read_text(encoding="utf-8")
    spec_source = (ROOT / "build.spec").read_text(encoding="utf-8")

    assert 'APP_VERSION = "1.3.0"' in version_source
    assert "from version import APP_NAME, APP_VERSION" in main_source
    assert "from version import APP_VERSION, BUNDLE_IDENTIFIER" in spec_source
    assert "collect_data_files(\"matplotlib\")" not in spec_source
    assert "analysis.datas = [entry for entry in analysis.datas if is_runtime_data(entry)]" in spec_source
    assert not (ROOT / "hooks" / "hook-matplotlib.py").exists()
    assert 'setApplicationVersion("' not in main_source
    assert "## 1.3.0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_only_one_entrypoint_and_one_pyinstaller_spec_exist():
    assert not (ROOT / "main.py").exists()
    assert [path.name for path in ROOT.glob("*.spec")] == ["build.spec"]


def test_local_builds_require_the_ci_python_version():
    macos_script = (ROOT / "build_macos.sh").read_text(encoding="utf-8")
    windows_script = (ROOT / "build_windows.bat").read_text(encoding="utf-8")

    assert "python3.12" in macos_script
    assert "sys.exit(0 if sys.version_info[:2] == (3, 12)" in macos_script
    assert "py -3.12" in windows_script
    assert "sys.exit(0 if sys.version_info[:2] == (3, 12)" in windows_script


def test_ci_covers_qa_and_three_release_archives():
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "macos-15-intel" in workflow
    assert "macos-14" in workflow
    assert "python -m pytest" in workflow
    assert "python -m pip check" in workflow
    assert "sudo apt-get install -y libegl1" in workflow
    uses = re.findall(r"uses:\s+([^\s#]+)", workflow)
    assert uses
    assert all(re.search(r"@[0-9a-f]{40}$", value) for value in uses)
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228" in workflow
    assert "ChzzkClipMomentCatcher-Windows-x86_64.zip" in workflow
    assert "ChzzkClipMomentCatcher-macOS-x86_64.zip" in workflow
    assert "ChzzkClipMomentCatcher-macOS-arm64.zip" in workflow
    assert "contents: read" in workflow
    assert "./package_macos.sh" in workflow
    assert "./smoke_windows.ps1" in workflow
    assert "verify_package_contents.py" in workflow
    assert workflow.count("--only-binary=:all:") == 3
    assert '"core.timeline"' in (ROOT / "build.spec").read_text(encoding="utf-8")


def test_macos_packaging_stages_before_signing_and_smoke_checks():
    script = (ROOT / "package_macos.sh").read_text(encoding="utf-8")

    assert "ditto --norsrc" in script
    assert "xattr -cr" in script
    assert "codesign --verify --deep --strict" in script
    assert "QT_QPA_PLATFORM=offscreen" in script
    assert '--smoke-test' in script


def test_windows_packaging_launches_the_built_executable():
    script = (ROOT / "smoke_windows.ps1").read_text(encoding="utf-8")

    assert "Start-Process" in script
    assert "Start-Sleep -Seconds 5" in script
    assert 'ArgumentList "--smoke-test"' in script
    assert "Packaged app exited during smoke test" in script


def test_runtime_and_build_dependencies_are_separated():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").casefold()
    development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").casefold()
    constraints = (ROOT / "constraints.txt").read_text(encoding="utf-8").casefold()

    assert "pyinstaller" not in runtime
    assert "pytest" not in runtime
    assert "pyinstaller" in development
    assert "pytest" in development
    assert "numpy==1.26.4" in runtime
    assert "pyinstaller==6.22.2" in development
    assert "pytest==9.1.1" in development
    assert "pillow==12.3.0" in runtime
    assert "-c constraints.txt" in runtime
    assert 'macholib==1.16.4; sys_platform == "darwin"' in constraints
    assert 'pefile==2024.8.26; sys_platform == "win32"' in constraints
    assert 'pywin32-ctypes==0.2.3; sys_platform == "win32"' in constraints


def test_readme_documents_real_csv_schema_and_export_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "재생시간,닉네임,id,메시지" in readme
    assert "편집 작업표 CSV" in readme
    assert "Premiere 교환 XML" in readme
    assert "CSV를 사용할 수 있습니다" in readme
    assert "타임라인 우클릭" not in readme


def test_repository_text_does_not_contain_stale_local_identity():
    forbidden = ("h" + "vs", "jerry" + "mouse", "your_" + "username")
    ignored_dirs = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        ".build-venv",
        "build",
        "dist",
        "venv",
        ".venv",
    }
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
