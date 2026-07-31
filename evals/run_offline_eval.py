from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from modeling_agent.config import Settings
from modeling_agent.runtime import build_runtime
from modeling_agent.tools import classify_problem

REQUIRED_PLAN_FIELDS = {
    "problem_summary",
    "subproblems",
    "problem_types",
    "candidate_models",
    "selected_model",
    "workflow",
    "validation_plan",
    "citations",
    "uncertainties",
    "paper_ready",
}


def load_cases(path: Path) -> list[dict[str, str]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


async def evaluate(cases: list[dict[str, str]], repo_root: Path) -> dict[str, Any]:
    runtime = build_runtime(
        Settings(
            app_mode="fake",
            knowledge_root=repo_root
            / "knowledge"
            / "math-modeling-skills"
            / "skills",
        )
    )
    if runtime.error or runtime.service is None:
        raise RuntimeError(runtime.error or "Runtime unavailable")

    correct = 0
    schema_valid = 0
    citation_valid = 0
    details = []
    for case in cases:
        predicted, _ = classify_problem(case["text"])
        matched = case["expected_type"] in {item.value for item in predicted}
        correct += int(matched)
        plan, _, _ = await runtime.service.agent.analyze(
            problem_text=case["text"],
            contest=None,
            constraints=[],
        )
        payload = plan.model_dump(mode="json")
        valid_schema = REQUIRED_PLAN_FIELDS.issubset(payload) and bool(plan.candidate_models)
        valid_citations = bool(plan.citations) and all(
            (
                repo_root
                / "knowledge"
                / "math-modeling-skills"
                / "skills"
                / citation.source_path
            ).exists()
            for citation in plan.citations
        )
        schema_valid += int(valid_schema)
        citation_valid += int(valid_citations)
        details.append(
            {
                "id": case["id"],
                "expected": case["expected_type"],
                "predicted": [item.value for item in predicted],
                "classification_ok": matched,
                "schema_ok": valid_schema,
                "citations_ok": valid_citations,
            }
        )

    total = len(cases)
    return {
        "case_count": total,
        "classification_accuracy": correct / total,
        "schema_valid_rate": schema_valid / total,
        "citation_valid_rate": citation_valid / total,
        "details": details,
    }


def render_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Offline Evaluation Report",
            "",
            f"- Cases: {result['case_count']}",
            f"- Classification accuracy: {result['classification_accuracy']:.1%}",
            f"- Schema valid rate: {result['schema_valid_rate']:.1%}",
            f"- Citation valid rate: {result['citation_valid_rate']:.1%}",
            "",
            "Acceptance: classification ≥ 80%, schema = 100%, citations = 100%.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    cases = load_cases(Path(__file__).with_name("synthetic-problems.jsonl"))
    result = asyncio.run(evaluate(cases, repo_root))
    print(render_markdown(result))
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "offline-eval.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (args.output_dir / "offline-eval.md").write_text(
            render_markdown(result),
            encoding="utf-8",
        )
    passed = (
        result["classification_accuracy"] >= 0.8
        and result["schema_valid_rate"] == 1.0
        and result["citation_valid_rate"] == 1.0
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
