from __future__ import annotations

from uuid import UUID, uuid4

from .agent import ModelingAgent
from .config import Settings
from .document_parser import parse_document, sanitize_filename
from .repositories import Repository
from .schemas import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    DocumentCreateResponse,
    DocumentRecord,
)


class NotFoundError(LookupError):
    pass


class ModelingService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        agent: ModelingAgent,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.agent = agent

    def create_document(self, filename: str, content: bytes) -> DocumentCreateResponse:
        text, media_type, sha256 = parse_document(
            filename,
            content,
            self.settings.max_upload_bytes,
        )
        record = DocumentRecord(
            id=uuid4(),
            filename=sanitize_filename(filename),
            media_type=media_type,
            sha256=sha256,
            text=text,
        )
        self.repository.save_document(record)
        return DocumentCreateResponse(
            document_id=record.id,
            filename=record.filename,
            media_type=record.media_type,
            character_count=len(record.text),
            sha256=record.sha256,
            preview=" ".join(record.text.split())[:240],
        )

    async def create_analysis_run(
        self,
        request: AnalysisRunRequest,
    ) -> AnalysisRunResponse:
        document = self.repository.get_document(request.document_id)
        if document is None:
            raise NotFoundError(f"Document {request.document_id} was not found.")
        plan, metrics, model = await self.agent.analyze(
            problem_text=document.text,
            contest=request.contest,
            constraints=request.constraints,
        )
        run = AnalysisRunResponse(
            run_id=uuid4(),
            document_id=document.id,
            status="completed",
            model=model,
            plan=plan,
            metrics=metrics,
        )
        self.repository.save_run(run)
        return run

    def get_analysis_run(self, run_id: UUID) -> AnalysisRunResponse:
        run = self.repository.get_run(run_id)
        if run is None:
            raise NotFoundError(f"Analysis run {run_id} was not found.")
        return run
