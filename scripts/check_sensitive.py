"""Fail when tracked project files appear to contain committed credentials."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]
IGNORED_NAMES = {".env.example", "check_sensitive.py"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    findings: list[str] = []
    for relative in result.stdout.splitlines():
        path = root / relative
        if not path.is_file() or path.name in IGNORED_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(relative)
                break
    if findings:
        print("Potential secrets found:")
        print("\n".join(f"- {path}" for path in findings))
        return 1
    print("Sensitive-value scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
