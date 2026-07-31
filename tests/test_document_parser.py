from __future__ import annotations

import pytest

from modeling_agent.document_parser import (
    DocumentParseError,
    parse_document,
    sanitize_filename,
)


def test_parse_markdown() -> None:
    text, media_type, digest = parse_document(
        "problem.md",
        "## 赛题\n请建立优化模型，在给定容量约束下制定资源分配方案并分析结果。".encode(),
        1024,
    )
    assert "优化模型" in text
    assert media_type == "text/markdown"
    assert len(digest) == 64


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("empty.txt", b"", "empty"),
        ("problem.csv", b"a,b\n1,2", "Only PDF"),
        ("tiny.txt", "太短".encode(), "enough text"),
    ],
)
def test_reject_invalid_documents(filename: str, content: bytes, message: str) -> None:
    with pytest.raises(DocumentParseError, match=message):
        parse_document(filename, content, 1024)


def test_reject_oversized_document() -> None:
    with pytest.raises(DocumentParseError, match="exceeds"):
        parse_document("problem.txt", b"x" * 50, 20)


def test_filename_is_reduced_to_basename() -> None:
    assert sanitize_filename("../../problem.md") == "problem.md"
