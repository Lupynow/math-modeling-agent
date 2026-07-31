from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from modeling_agent.knowledge import QdrantKnowledgeStore
from modeling_agent.providers import HashEmbeddingProvider
from modeling_agent.repositories import MySQLRepository
from modeling_agent.schemas import DocumentRecord

pytestmark = pytest.mark.integration


def integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not integration_enabled(), reason="set RUN_INTEGRATION=1")
def test_mysql_document_round_trip() -> None:
    repository = MySQLRepository(
        os.getenv(
            "MYSQL_TEST_URL",
            "mysql+pymysql://modeling:modeling@127.0.0.1:3306/modeling",
        )
    )
    document = DocumentRecord(
        id=uuid4(),
        filename="integration.md",
        media_type="text/markdown",
        sha256="a" * 64,
        text="这是一条用于 MySQL 集成测试的数学建模赛题文本。",
    )
    repository.save_document(document)
    loaded = repository.get_document(document.id)
    assert loaded is not None
    assert loaded.model_dump() == document.model_dump()
    assert repository.ping()


@pytest.mark.skipif(not integration_enabled(), reason="set RUN_INTEGRATION=1")
def test_qdrant_idempotent_reindex_and_search() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    collection = f"integration_{uuid4().hex}"
    store = QdrantKnowledgeStore(
        knowledge_root=repo_root / "knowledge" / "math-modeling-skills" / "skills",
        embedder=HashEmbeddingProvider(),
        url=os.getenv("QDRANT_TEST_URL", "http://127.0.0.1:6333"),
        collection=collection,
    )
    try:
        first_count = store.reindex()
        second_count = store.reindex()
        hits = store.search("优化 调度 约束", limit=3)
        assert first_count == second_count
        assert first_count > 0
        assert hits
        assert all(hit.source_path and hit.section for hit in hits)
    finally:
        store.client.delete_collection(collection)
