from pathlib import Path

from scripts.verify_package_contents import verify


def test_package_verifier_accepts_runtime_files(tmp_path: Path):
    (tmp_path / "ChzzkClipMomentCatcher").write_bytes(b"binary")
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "stopwords").write_text("chat", encoding="utf-8")

    assert verify(tmp_path) == []


def test_package_verifier_rejects_development_files(tmp_path: Path):
    tests = tmp_path / "vendor" / "tests"
    tests.mkdir(parents=True)
    source = tmp_path / "private_module.py"
    source.write_text("secret = True", encoding="utf-8")
    (tests / "fixture.dat").write_bytes(b"fixture")

    violations = {path.as_posix() for path in verify(tmp_path)}

    assert "private_module.py" in violations
    assert "vendor/tests" in violations
    assert "vendor/tests/fixture.dat" in violations
