from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from modeling_agent.config import Settings
from modeling_agent.main import create_app


def make_client() -> TestClient:
    knowledge_root = (
        Path(__file__).resolve().parents[1]
        / "knowledge"
        / "math-modeling-skills"
        / "skills"
    )
    app = create_app(Settings(app_mode="fake", knowledge_root=knowledge_root))
    return TestClient(app)


def test_health_ready_and_metrics() -> None:
    with make_client() as client:
        assert client.get("/health").json() == {"status": "ok"}
        ready = client.get("/ready").json()
        assert ready["ready"] is True
        assert all(ready["dependencies"].values())
        assert "modeling_agent_requests_total" in client.get("/metrics").text


def test_document_to_analysis_flow() -> None:
    with make_client() as client:
        upload = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "problem.md",
                    "## 任务\n根据历史需求预测未来销量，并在容量约束下优化配送方案。",
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 201
        document_id = upload.json()["document_id"]

        analysis = client.post(
            "/api/v1/analysis-runs",
            json={
                "document_id": document_id,
                "contest": "CUMCM",
                "constraints": ["结果必须可解释"],
            },
        )
        assert analysis.status_code == 201
        body = analysis.json()
        assert body["status"] == "completed"
        assert body["plan"]["schema_version"] == "1.0"
        assert len(body["plan"]["candidate_models"]) >= 2
        assert body["plan"]["citations"]
        assert body["plan"]["paper_ready_markdown"].startswith("[PAPER_READY]")

        fetched = client.get(f"/api/v1/analysis-runs/{body['run_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["run_id"] == body["run_id"]


def test_invalid_upload_and_missing_run() -> None:
    with make_client() as client:
        upload = client.post(
            "/api/v1/documents",
            files={"file": ("data.csv", "a,b\n1,2", "text/csv")},
        )
        assert upload.status_code == 422
        assert upload.json()["code"] == "invalid_document"

        missing = client.get(f"/api/v1/analysis-runs/{uuid4()}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"


def test_unconfigured_production_mode_is_not_ready() -> None:
    app = create_app(
        Settings(
            app_mode="production",
            chat_api_base="",
            chat_api_key="",
            chat_model="",
            embedding_api_base="",
            embedding_api_key="",
            embedding_model="",
        )
    )
    with TestClient(app) as client:
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["ready"] is False

        response = client.post(
            "/api/v1/analysis-runs",
            json={"document_id": str(uuid4())},
        )
        assert response.status_code == 503
        assert response.json()["code"] == "http_error"
