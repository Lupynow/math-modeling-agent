from uuid import uuid4

from modeling_agent.repositories import MySQLRepository
from modeling_agent.schemas import DocumentRecord


def test_sql_repository_mapping_and_document_round_trip(tmp_path) -> None:
    database_path = tmp_path / "repository.db"
    repository = MySQLRepository(f"sqlite+pysqlite:///{database_path.as_posix()}")
    document = DocumentRecord(
        id=uuid4(),
        filename="repository-test.md",
        media_type="text/markdown",
        sha256="b" * 64,
        text="A small repository regression test.",
    )

    repository.save_document(document)

    loaded = repository.get_document(document.id)
    assert loaded is not None
    assert loaded.model_dump() == document.model_dump()
    assert repository.ping()
