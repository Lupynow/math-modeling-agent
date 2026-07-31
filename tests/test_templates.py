from __future__ import annotations

import ast
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_all_python_templates_parse() -> None:
    templates = sorted(
        repo_root().glob(
            "knowledge/math-modeling-skills/skills/**/references/code-templates/python/**/*.py"
        )
    )
    assert len(templates) == 22
    for template in templates:
        ast.parse(template.read_text(encoding="utf-8"), filename=str(template))


def test_matlab_templates_are_non_empty_and_structured() -> None:
    templates = sorted(
        repo_root().glob(
            "knowledge/math-modeling-skills/skills/**/references/code-templates/matlab/**/*.m"
        )
    )
    assert len(templates) == 7
    for template in templates:
        text = template.read_text(encoding="utf-8")
        assert len(text.strip()) > 100
        assert "%" in text
