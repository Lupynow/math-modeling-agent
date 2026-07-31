from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Text, create_engine, text
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .schemas import AnalysisPlan, AnalysisRunResponse, DocumentRecord, RunMetrics


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Repository(ABC):
    @abstractmethod
    def save_document(self, document: DocumentRecord) -> None: ...

    @abstractmethod
    def get_document(self, document_id: UUID) -> DocumentRecord | None: ...

    @abstractmethod
    def save_run(self, run: AnalysisRunResponse) -> None: ...

    @abstractmethod
    def get_run(self, run_id: UUID) -> AnalysisRunResponse | None: ...

    @abstractmethod
    def ping(self) -> bool: ...


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self.documents: dict[UUID, DocumentRecord] = {}
        self.runs: dict[UUID, AnalysisRunResponse] = {}

    def save_document(self, document: DocumentRecord) -> None:
        self.documents[document.id] = document

    def get_document(self, document_id: UUID) -> DocumentRecord | None:
        return self.documents.get(document_id)

    def save_run(self, run: AnalysisRunResponse) -> None:
        self.runs[run.run_id] = run

    def get_run(self, run_id: UUID) -> AnalysisRunResponse | None:
        return self.runs.get(run_id)

    def ping(self) -> bool:
        return True


class MySQLRepository(Repository):
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, pool_pre_ping=True)
        timestamp_type = (
            MySQLDateTime(fsp=6)
            if self._engine.dialect.name == "mysql"
            else DateTime(timezone=True)
        )

        class Base(DeclarativeBase):
            pass

        class DocumentRow(Base):
            __tablename__ = "documents"

            id: Mapped[str] = mapped_column(String(36), primary_key=True)
            filename: Mapped[str] = mapped_column(String(255))
            media_type: Mapped[str] = mapped_column(String(100))
            sha256: Mapped[str] = mapped_column(String(64), index=True)
            text: Mapped[str] = mapped_column(Text)
            created_at: Mapped[datetime] = mapped_column(timestamp_type)

        class AnalysisRunRow(Base):
            __tablename__ = "analysis_runs"

            id: Mapped[str] = mapped_column(String(36), primary_key=True)
            document_id: Mapped[str] = mapped_column(String(36), index=True)
            status: Mapped[str] = mapped_column(String(32))
            model: Mapped[str] = mapped_column(String(255))
            schema_version: Mapped[str] = mapped_column(String(32))
            prompt_version: Mapped[str] = mapped_column(String(64))
            output_json: Mapped[dict[str, Any]] = mapped_column(JSON)
            latency_ms: Mapped[int]
            prompt_tokens: Mapped[int]
            completion_tokens: Mapped[int]
            retrieval_hits: Mapped[int]
            tool_success_rate: Mapped[float]
            created_at: Mapped[datetime] = mapped_column(timestamp_type)

        class RetrievalHitRow(Base):
            __tablename__ = "retrieval_hits"

            id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
            run_id: Mapped[str] = mapped_column(String(36), index=True)
            source_path: Mapped[str] = mapped_column(String(500))
            section: Mapped[str] = mapped_column(String(500))
            score: Mapped[float]

        class EvaluationResultRow(Base):
            __tablename__ = "evaluation_results"

            id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
            run_id: Mapped[str] = mapped_column(String(36), index=True)
            metric_name: Mapped[str] = mapped_column(String(100))
            metric_value: Mapped[float]
            details_json: Mapped[dict[str, Any]] = mapped_column(JSON)

        self._DocumentRow = DocumentRow
        self._AnalysisRunRow = AnalysisRunRow
        self._RetrievalHitRow = RetrievalHitRow
        self._session = sessionmaker(self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)

    def save_document(self, document: DocumentRecord) -> None:
        with self._session.begin() as session:
            session.merge(
                self._DocumentRow(
                    id=str(document.id),
                    filename=document.filename,
                    media_type=document.media_type,
                    sha256=document.sha256,
                    text=document.text,
                    created_at=document.created_at,
                )
            )

    def get_document(self, document_id: UUID) -> DocumentRecord | None:
        with self._session() as session:
            row = session.get(self._DocumentRow, str(document_id))
            if row is None:
                return None
            return DocumentRecord(
                id=UUID(row.id),
                filename=row.filename,
                media_type=row.media_type,
                sha256=row.sha256,
                text=row.text,
                created_at=_as_utc(row.created_at),
            )

    def save_run(self, run: AnalysisRunResponse) -> None:
        payload = json.loads(run.plan.model_dump_json())
        with self._session.begin() as session:
            session.merge(
                self._AnalysisRunRow(
                    id=str(run.run_id),
                    document_id=str(run.document_id),
                    status=run.status,
                    model=run.model,
                    schema_version=run.plan.schema_version,
                    prompt_version=run.plan.prompt_version,
                    output_json=payload,
                    latency_ms=run.metrics.latency_ms,
                    prompt_tokens=run.metrics.prompt_tokens,
                    completion_tokens=run.metrics.completion_tokens,
                    retrieval_hits=run.metrics.retrieval_hits,
                    tool_success_rate=run.metrics.tool_success_rate,
                    created_at=run.created_at,
                )
            )
            for citation in run.plan.citations:
                session.add(
                    self._RetrievalHitRow(
                        run_id=str(run.run_id),
                        source_path=citation.source_path,
                        section=citation.section,
                        score=citation.score,
                    )
                )

    def get_run(self, run_id: UUID) -> AnalysisRunResponse | None:
        with self._session() as session:
            row = session.get(self._AnalysisRunRow, str(run_id))
            if row is None:
                return None
            return AnalysisRunResponse(
                run_id=UUID(row.id),
                document_id=UUID(row.document_id),
                status=row.status,
                model=row.model,
                created_at=_as_utc(row.created_at),
                plan=AnalysisPlan.model_validate(row.output_json),
                metrics=RunMetrics(
                    latency_ms=row.latency_ms,
                    prompt_tokens=row.prompt_tokens,
                    completion_tokens=row.completion_tokens,
                    retrieval_hits=row.retrieval_hits,
                    tool_success_rate=row.tool_success_rate,
                ),
            )

    def ping(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
