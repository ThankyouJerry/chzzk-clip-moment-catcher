"""Keep application, changelog, and pushed release tag versions aligned."""

from __future__ import annotations

import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from version import APP_VERSION  # noqa: E402


def main() -> int:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = re.compile(rf"^## {re.escape(APP_VERSION)}(?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?\s*$", re.MULTILINE)
    if heading.search(changelog) is None:
        print(f"CHANGELOG.md has no section for {APP_VERSION}")
        return 1
    github_ref = os.environ.get("GITHUB_REF", "")
    if github_ref.startswith("refs/tags/"):
        tag = github_ref.removeprefix("refs/tags/")
        expected = f"v{APP_VERSION}"
        if tag != expected:
            print(f"release tag {tag!r} does not match application version {expected!r}")
            return 1
    print(f"release metadata verified: {APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
