from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProblemType(StrEnum):
    FORECASTING = "forecasting"
    CLASSIFICATION = "classification"
    EVALUATION = "evaluation"
    OPTIMIZATION = "optimization"
    MECHANISTIC = "mechanistic"
    STATISTICAL = "statistical"
    NETWORK = "network"
    CLUSTERING = "clustering"
    GAME_THEORY = "game_theory"
    ECOLOGICAL = "ecological"
    GEOMETRIC = "geometric"
    SIMULATION = "simulation"


class DocumentRecord(BaseModel):
    id: UUID
    filename: str
    media_type: str
    sha256: str
    text: str
    created_at: datetime = Field(default_factory=utc_now)


class DocumentCreateResponse(BaseModel):
    document_id: UUID
    filename: str
    media_type: str
    character_count: int
    sha256: str
    preview: str


class AnalysisRunRequest(BaseModel):
    document_id: UUID
    contest: str | None = None
    constraints: list[str] = Field(default_factory=list, max_length=20)
    interaction_mode: str = Field(default="auto", pattern="^(guided|auto)$")


class EvidenceCitation(BaseModel):
    source_path: str
    section: str
    excerpt: str
    score: float = Field(ge=0, le=1)


class CandidateModel(BaseModel):
    name: str
    rationale: str
    prerequisites: list[str] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool: str
    status: str
    summary: str


class PaperReadyPackage(BaseModel):
    schema_version: str = "1.0"
    problem_summary: str
    subproblems: list[str]
    assumptions: list[str]
    candidate_models: list[CandidateModel]
    selected_model: CandidateModel
    workflow: list[str]
    validation_plan: list[str]
    limitations: list[str]
    citations: list[EvidenceCitation]
    unresolved_questions: list[str]
    status: str = Field(default="planned", pattern="^(planned|partial|completed)$")


class AnalysisPlan(BaseModel):
    schema_version: str = "1.0"
    prompt_version: str
    problem_summary: str
    subproblems: list[str]
    problem_types: list[ProblemType]
    classification_rationale: str
    data_requirements: list[str]
    assumptions: list[str]
    candidate_models: list[CandidateModel]
    selected_model: CandidateModel
    workflow: list[str]
    tool_calls: list[ToolCallRecord]
    validation_plan: list[str]
    citations: list[EvidenceCitation]
    uncertainties: list[str]
    paper_ready: PaperReadyPackage
    paper_ready_markdown: str


class RunMetrics(BaseModel):
    latency_ms: int = Field(ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    retrieval_hits: int = Field(default=0, ge=0)
    tool_success_rate: float = Field(default=1.0, ge=0, le=1)


class AnalysisRunResponse(BaseModel):
    run_id: UUID
    document_id: UUID
    status: str
    model: str
    created_at: datetime = Field(default_factory=utc_now)
    plan: AnalysisPlan
    metrics: RunMetrics


class ReadyResponse(BaseModel):
    ready: bool
    mode: str
    dependencies: dict[str, bool]


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
