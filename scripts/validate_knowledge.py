"""Validate the read-only mathematical-modeling knowledge submodule."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*]\(([^)]+)\)")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    knowledge_root = repo_root / "knowledge" / "math-modeling-skills"
    skills_root = knowledge_root / "skills"
    errors: list[str] = []

    for skill_name in ("math-modeling-solver", "math-modeling-paper"):
        if not (skills_root / skill_name / "SKILL.md").exists():
            errors.append(f"missing knowledge skill: {skill_name}")

    python_templates = sorted(
        skills_root.glob("**/references/code-templates/python/**/*.py")
    )
    matlab_templates = sorted(
        skills_root.glob("**/references/code-templates/matlab/**/*.m")
    )
    if len(python_templates) != 22:
        errors.append(f"expected 22 Python templates, found {len(python_templates)}")
    if len(matlab_templates) != 7:
        errors.append(f"expected 7 MATLAB templates, found {len(matlab_templates)}")
    for template in python_templates:
        try:
            ast.parse(template.read_text(encoding="utf-8"), filename=str(template))
        except SyntaxError as exc:
            errors.append(f"{template}: {exc}")

    for markdown in skills_root.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            local_target = target.split("#", 1)[0].strip()
            if (
                not local_target
                or "://" in local_target
                or local_target.startswith(("#", "mailto:"))
            ):
                continue
            if not (markdown.parent / local_target).resolve().exists():
                errors.append(f"{markdown}: broken link {target!r}")

    project_markdown = [repo_root / "README.md", *sorted((repo_root / "docs").glob("*.md"))]
    for markdown in project_markdown:
        text = markdown.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            local_target = target.split("#", 1)[0].strip()
            if (
                not local_target
                or "://" in local_target
                or local_target.startswith(("#", "mailto:"))
            ):
                continue
            if not (markdown.parent / local_target).resolve().exists():
                errors.append(f"{markdown}: broken project link {target!r}")

    schema_path = repo_root / "schemas" / "paper-ready.schema.json"
    try:
        json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{schema_path}: {exc}")

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(
        "Knowledge validation passed "
        f"({len(python_templates)} Python, {len(matlab_templates)} MATLAB templates)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
