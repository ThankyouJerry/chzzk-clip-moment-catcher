"""Reject development and sample files from a packaged application tree."""

from __future__ import annotations

from pathlib import Path
import sys


FORBIDDEN_DIRECTORY_NAMES = {
    "__pycache__",
    "examples",
    "sample_data",
    "test",
    "tests",
}
FORBIDDEN_SUFFIXES = {".py", ".pyc", ".pyo"}


def verify(root: Path) -> list[Path]:
    violations = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        lowered_parts = {part.casefold() for part in relative.parts}
        if lowered_parts & FORBIDDEN_DIRECTORY_NAMES:
            violations.append(relative)
        elif path.is_file() and path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            violations.append(relative)
    return violations


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_package_contents.py <package-directory>")
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"package directory not found: {root}")
        return 2
    violations = verify(root)
    if violations:
        print("development files found in package:")
        for path in violations[:50]:
            print(f"- {path}")
        return 1
    print(f"package contents verified: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
