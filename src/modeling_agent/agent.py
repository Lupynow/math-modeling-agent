from __future__ import annotations

from time import perf_counter

from pydantic import ValidationError

from .config import Settings
from .knowledge import KnowledgeStore
from .providers import ChatProvider, ProviderError
from .schemas import (
    AnalysisPlan,
    CandidateModel,
    PaperReadyPackage,
    RunMetrics,
    ToolCallRecord,
)
from .tools import (
    classify_problem,
    recommend_candidate_models,
    render_paper_ready,
    retrieve_modeling_knowledge,
    validate_analysis_plan,
)


class AgentError(RuntimeError):
    pass


def _string_list(value: object, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or fallback


class ModelingAgent:
    def __init__(
        self,
        *,
        settings: Settings,
        chat_provider: ChatProvider,
        knowledge_store: KnowledgeStore,
    ) -> None:
        self.settings = settings
        self.chat_provider = chat_provider
        self.knowledge_store = knowledge_store

    async def analyze(
        self,
        *,
        problem_text: str,
        contest: str | None,
        constraints: list[str],
    ) -> tuple[AnalysisPlan, RunMetrics, str]:
        started = perf_counter()
        tool_calls: list[ToolCallRecord] = []

        problem_types, rationale = classify_problem(problem_text)
        tool_calls.append(
            ToolCallRecord(
                tool="classify_problem",
                status="success",
                summary=", ".join(item.value for item in problem_types),
            )
        )

        citations = retrieve_modeling_knowledge(
            self.knowledge_store,
            f"{problem_text[:1200]}\ncontest={contest or 'unspecified'}",
        )
        tool_calls.append(
            ToolCallRecord(
                tool="retrieve_modeling_knowledge",
                status="success" if citations else "warning",
                summary=f"{len(citations)} retrieval hits",
            )
        )

        candidates = recommend_candidate_models(problem_types)
        tool_calls.append(
            ToolCallRecord(
                tool="recommend_candidate_models",
                status="success",
                summary=", ".join(model.name for model in candidates),
            )
        )

        knowledge_context = "\n".join(
            f"- {citation.source_path}#{citation.section}: {citation.excerpt}"
            for citation in citations[:5]
        )
        prompt = (
            "Analyze the problem without inventing data. Return structured JSON.\n\n"
            f"CONTEST: {contest or 'unspecified'}\n"
            f"CONSTRAINTS: {constraints}\n"
            f"PROBLEM_TEXT:\n{problem_text[:12000]}\n\n"
            f"KNOWLEDGE:\n{knowledge_context}"
        )
        try:
            completion = await self.chat_provider.complete_json(prompt)
        except ProviderError as exc:
            raise AgentError(str(exc)) from exc

        data = completion.data
        summary = str(data.get("problem_summary", "")).strip() or problem_text[:180]
        subproblems = _string_list(
            data.get("subproblems"),
            ["明确目标、变量与约束", "建立候选模型并验证"],
        )
        data_requirements = _string_list(
            data.get("data_requirements"),
            ["赛题原始数据", "变量单位、时间范围和缺失值说明"],
        )
        assumptions = _string_list(
            data.get("assumptions"),
            ["输入数据口径一致", "分析期内未说明的外部条件保持稳定"],
        )
        uncertainties = _string_list(
            data.get("uncertainties"),
            ["参数、假设与模型效果需要使用实际数据验证"],
        )
        workflow = [
            "检查数据口径、单位、缺失值和异常值",
            f"围绕 {', '.join(item.value for item in problem_types)} 构造可检验变量",
            f"建立 {candidates[0].name} 并实现可复现基线",
            f"使用 {candidates[1].name} 作为备选进行对照",
            "执行误差、灵敏度或鲁棒性检验并记录失败情形",
            "整理图表、引用和 PAPER_READY 论文交接包",
        ]
        validation_plan = [
            "划分训练/验证或基准/扰动场景，避免数据泄漏",
            "对关键参数执行 ±5%、±10% 扰动并比较结论变化",
            "与至少一个简单基线比较效果、稳定性和解释性",
        ]
        issues = validate_analysis_plan(
            candidates=candidates,
            citations=citations,
            workflow=workflow,
        )
        tool_calls.append(
            ToolCallRecord(
                tool="validate_analysis_plan",
                status="success" if not issues else "warning",
                summary="; ".join(issues) if issues else "schema and evidence checks passed",
            )
        )
        uncertainties.extend(issue for issue in issues if issue not in uncertainties)

        selected: CandidateModel = candidates[0]
        package = PaperReadyPackage(
            schema_version=self.settings.schema_version,
            problem_summary=summary,
            subproblems=subproblems,
            assumptions=assumptions,
            candidate_models=candidates,
            selected_model=selected,
            workflow=workflow,
            validation_plan=validation_plan,
            limitations=uncertainties,
            citations=citations,
            unresolved_questions=uncertainties,
            status="planned",
        )
        markdown = render_paper_ready(package)
        tool_calls.append(
            ToolCallRecord(
                tool="render_paper_ready",
                status="success",
                summary="generated JSON and Markdown handoff",
            )
        )

        try:
            plan = AnalysisPlan(
                schema_version=self.settings.schema_version,
                prompt_version=self.settings.prompt_version,
                problem_summary=summary,
                subproblems=subproblems,
                problem_types=problem_types,
                classification_rationale=rationale,
                data_requirements=data_requirements,
                assumptions=assumptions,
                candidate_models=candidates,
                selected_model=selected,
                workflow=workflow,
                tool_calls=tool_calls,
                validation_plan=validation_plan,
                citations=citations,
                uncertainties=uncertainties,
                paper_ready=package,
                paper_ready_markdown=markdown,
            )
        except ValidationError as exc:
            raise AgentError("The generated analysis did not match the required schema.") from exc

        successful = sum(call.status == "success" for call in tool_calls)
        metrics = RunMetrics(
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            retrieval_hits=len(citations),
            tool_success_rate=successful / len(tool_calls),
        )
        return plan, metrics, completion.model
