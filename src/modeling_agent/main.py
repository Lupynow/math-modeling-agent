from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from .agent import AgentError
from .config import Settings, get_settings
from .document_parser import DocumentParseError
from .metrics import metrics
from .runtime import Runtime, build_runtime
from .schemas import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    ApiError,
    DocumentCreateResponse,
    ReadyResponse,
)
from .service import NotFoundError


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime = build_runtime(active_settings)
        yield

    app = FastAPI(
        title=active_settings.app_name,
        version="2.0.0",
        description="Evidence-backed mathematical modeling problem analysis agent.",
        lifespan=lifespan,
    )
    app.state.runtime = Runtime(None, None, None, "Application has not started.")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(int((perf_counter() - started) * 1000))
        endpoint = request.url.path.replace("/", "_").strip("_") or "root"
        metrics.increment(f'modeling_agent_requests_total{{endpoint="{endpoint}"}}')
        return response

    def error_response(request: Request, code: str, message: str, http_status: int) -> JSONResponse:
        payload = ApiError(
            code=code,
            message=message,
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=http_status, content=payload.model_dump(mode="json"))

    @app.exception_handler(DocumentParseError)
    async def document_error(request: Request, exc: DocumentParseError):
        return error_response(
            request,
            "invalid_document",
            str(exc),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error(request: Request, exc: NotFoundError):
        return error_response(request, "not_found", str(exc), status.HTTP_404_NOT_FOUND)

    @app.exception_handler(AgentError)
    async def agent_error(request: Request, exc: AgentError):
        return error_response(request, "agent_failed", str(exc), status.HTTP_502_BAD_GATEWAY)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        payload = ApiError(
            code="validation_error",
            message="Request validation failed.",
            request_id=getattr(request.state, "request_id", None),
            details={"errors": exc.errors()},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(request, "http_error", str(exc.detail), exc.status_code)

    def require_runtime(request: Request) -> Runtime:
        runtime: Runtime = request.app.state.runtime
        if runtime.service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=runtime.error or "Service dependencies are unavailable.",
            )
        return runtime

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", response_model=ReadyResponse)
    async def ready(request: Request) -> ReadyResponse:
        runtime: Runtime = request.app.state.runtime
        database_ok = bool(runtime.repository and runtime.repository.ping())
        qdrant_ok = bool(runtime.knowledge_store and runtime.knowledge_store.ping())
        model_ok = active_settings.model_configured
        return ReadyResponse(
            ready=bool(runtime.service and database_ok and qdrant_ok and model_ok),
            mode=active_settings.app_mode,
            dependencies={
                "database": database_ok,
                "qdrant": qdrant_ok,
                "model": model_ok,
            },
        )

    @app.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics() -> str:
        return metrics.render()

    @app.post(
        "/api/v1/documents",
        response_model=DocumentCreateResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_document(request: Request, file: Annotated[UploadFile, File()]):
        runtime = require_runtime(request)
        assert runtime.service is not None
        content = await file.read(active_settings.max_upload_bytes + 1)
        return runtime.service.create_document(file.filename or "upload.txt", content)

    @app.post(
        "/api/v1/analysis-runs",
        response_model=AnalysisRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_analysis_run(request: Request, payload: AnalysisRunRequest):
        runtime = require_runtime(request)
        assert runtime.service is not None
        return await runtime.service.create_analysis_run(payload)

    @app.get("/api/v1/analysis-runs/{run_id}", response_model=AnalysisRunResponse)
    async def get_analysis_run(request: Request, run_id: UUID):
        runtime = require_runtime(request)
        assert runtime.service is not None
        return runtime.service.get_analysis_run(run_id)

    return app


app = create_app()
