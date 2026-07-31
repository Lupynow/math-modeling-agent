from __future__ import annotations

from collections.abc import Iterable

from .knowledge import KnowledgeStore
from .schemas import CandidateModel, EvidenceCitation, PaperReadyPackage, ProblemType

KEYWORDS: dict[ProblemType, tuple[str, ...]] = {
    ProblemType.FORECASTING: ("预测", "趋势", "时间序列", "forecast", "未来"),
    ProblemType.CLASSIFICATION: ("分类", "识别", "判别", "classification", "标签"),
    ProblemType.EVALUATION: ("评价", "排名", "指标体系", "topsis", "综合得分"),
    ProblemType.OPTIMIZATION: ("优化", "最优", "调度", "分配", "路径", "成本最小"),
    ProblemType.MECHANISTIC: ("微分方程", "机理", "传热", "动力学", "ode"),
    ProblemType.STATISTICAL: ("显著性", "相关性", "回归", "方差分析", "统计"),
    ProblemType.NETWORK: ("网络", "节点", "图论", "最短路", "传播"),
    ProblemType.CLUSTERING: ("聚类", "分群", "相似群体", "cluster"),
    ProblemType.GAME_THEORY: ("博弈", "策略互动", "纳什", "竞争", "合作"),
    ProblemType.ECOLOGICAL: ("生态", "环境", "污染", "种群", "碳排放"),
    ProblemType.GEOMETRIC: ("几何", "轨迹", "运动学", "空间位置", "碰撞"),
    ProblemType.SIMULATION: ("仿真", "蒙特卡洛", "随机模拟", "simulation", "排队"),
}


MODEL_LIBRARY: dict[ProblemType, tuple[CandidateModel, CandidateModel]] = {
    ProblemType.FORECASTING: (
        CandidateModel(
            name="时间序列基线模型",
            rationale="适合按时间排序且存在趋势或周期的数据。",
            prerequisites=["连续时间索引", "足够历史观测"],
            advantages=["解释清晰", "便于建立基线"],
            risks=["结构突变时性能下降"],
        ),
        CandidateModel(
            name="梯度提升回归",
            rationale="适合存在多维外生变量和非线性关系的预测问题。",
            prerequisites=["可构造稳定特征"],
            advantages=["非线性拟合能力强"],
            risks=["时间泄漏和过拟合"],
        ),
    ),
    ProblemType.CLASSIFICATION: (
        CandidateModel(
            name="逻辑回归",
            rationale="提供可解释的分类基线。",
            prerequisites=["有标签样本"],
            advantages=["训练稳定", "系数可解释"],
            risks=["难以表达复杂非线性边界"],
        ),
        CandidateModel(
            name="随机森林",
            rationale="可处理非线性和变量交互。",
            prerequisites=["有标签样本"],
            advantages=["鲁棒", "可输出特征重要性"],
            risks=["概率校准可能较差"],
        ),
    ),
    ProblemType.EVALUATION: (
        CandidateModel(
            name="熵权-TOPSIS",
            rationale="适合多指标综合评价并减少主观赋权。",
            prerequisites=["指标方向和量纲可统一"],
            advantages=["流程透明"],
            risks=["结果受归一化方式影响"],
        ),
        CandidateModel(
            name="主成分分析",
            rationale="适合高度相关指标的降维评价。",
            prerequisites=["连续数值指标"],
            advantages=["降低冗余"],
            risks=["主成分含义可能不直观"],
        ),
    ),
    ProblemType.OPTIMIZATION: (
        CandidateModel(
            name="混合整数规划",
            rationale="适合目标和约束可明确表达的离散决策问题。",
            prerequisites=["决策变量和约束可数学化"],
            advantages=["可解释且可验证最优性"],
            risks=["大规模问题求解时间增加"],
        ),
        CandidateModel(
            name="遗传算法",
            rationale="适合非凸、非光滑或黑箱目标。",
            prerequisites=["可定义适应度与可行性修复"],
            advantages=["模型形式灵活"],
            risks=["不保证全局最优且需调参"],
        ),
    ),
    ProblemType.MECHANISTIC: (
        CandidateModel(
            name="常微分方程模型",
            rationale="适合描述状态随时间的连续演化。",
            prerequisites=["可提出守恒或变化率关系"],
            advantages=["机理可解释"],
            risks=["参数辨识可能不稳定"],
        ),
        CandidateModel(
            name="数据驱动代理模型",
            rationale="在机理不完整时近似输入输出关系。",
            prerequisites=["足够覆盖的数据"],
            advantages=["计算速度快"],
            risks=["外推能力有限"],
        ),
    ),
    ProblemType.STATISTICAL: (
        CandidateModel(
            name="多元回归与假设检验",
            rationale="适合量化变量关联并检验统计显著性。",
            prerequisites=["满足或可修正模型假设"],
            advantages=["推断体系成熟"],
            risks=["相关关系不能直接解释为因果"],
        ),
        CandidateModel(
            name="Bootstrap 重采样",
            rationale="适合分布假设较弱时估计不确定性。",
            prerequisites=["样本具有代表性"],
            advantages=["分布依赖较少"],
            risks=["小样本偏差仍会被保留"],
        ),
    ),
    ProblemType.NETWORK: (
        CandidateModel(
            name="图网络中心性与社区分析",
            rationale="适合识别关键节点和群落结构。",
            prerequisites=["可构建节点和边"],
            advantages=["结构解释直观"],
            risks=["结果依赖建图规则"],
        ),
        CandidateModel(
            name="网络流模型",
            rationale="适合容量约束下的运输或资源流动。",
            prerequisites=["边容量和成本可定义"],
            advantages=["存在成熟精确算法"],
            risks=["动态变化需要扩展模型"],
        ),
    ),
    ProblemType.CLUSTERING: (
        CandidateModel(
            name="K-Means",
            rationale="适合近似球形且规模较大的数值样本。",
            prerequisites=["合理标准化并选择簇数"],
            advantages=["简单高效"],
            risks=["对异常值和初值敏感"],
        ),
        CandidateModel(
            name="DBSCAN",
            rationale="适合存在噪声和不规则簇形状的数据。",
            prerequisites=["可确定距离与邻域参数"],
            advantages=["无需预设簇数"],
            risks=["不同密度簇较难处理"],
        ),
    ),
    ProblemType.GAME_THEORY: (
        CandidateModel(
            name="静态博弈与 Nash 均衡",
            rationale="适合参与者同时选择且收益可定义的策略问题。",
            prerequisites=["参与者、策略和收益明确"],
            advantages=["均衡含义清晰"],
            risks=["多均衡时需要选择机制"],
        ),
        CandidateModel(
            name="演化博弈",
            rationale="适合有限理性群体策略随时间演化。",
            prerequisites=["可定义复制动态或更新规则"],
            advantages=["可分析长期稳定策略"],
            risks=["参数估计困难"],
        ),
    ),
    ProblemType.ECOLOGICAL: (
        CandidateModel(
            name="系统动力学模型",
            rationale="适合具有反馈回路的生态环境系统。",
            prerequisites=["关键库存、流量和反馈关系明确"],
            advantages=["支持情景分析"],
            risks=["结构和参数不确定性较大"],
        ),
        CandidateModel(
            name="多指标环境评价",
            rationale="适合综合衡量环境状态或政策效果。",
            prerequisites=["指标体系和权重可解释"],
            advantages=["结果便于比较"],
            risks=["权重选择影响排名"],
        ),
    ),
    ProblemType.GEOMETRIC: (
        CandidateModel(
            name="解析几何与运动学",
            rationale="适合轨迹、位置和碰撞关系可显式推导的问题。",
            prerequisites=["坐标系和运动约束明确"],
            advantages=["精度和解释性高"],
            risks=["复杂边界下推导困难"],
        ),
        CandidateModel(
            name="离散事件仿真",
            rationale="适合复杂几何约束和事件触发过程。",
            prerequisites=["时间步长与碰撞规则明确"],
            advantages=["适应复杂场景"],
            risks=["离散误差需要验证"],
        ),
    ),
    ProblemType.SIMULATION: (
        CandidateModel(
            name="Monte Carlo 仿真",
            rationale="适合传播输入不确定性并估计结果分布。",
            prerequisites=["可定义随机变量分布"],
            advantages=["实现通用"],
            risks=["低概率事件需要大量样本"],
        ),
        CandidateModel(
            name="离散事件仿真",
            rationale="适合排队、服务和资源竞争过程。",
            prerequisites=["事件、状态和转移规则明确"],
            advantages=["能还原动态过程"],
            risks=["验证和校准成本较高"],
        ),
    ),
}


def classify_problem(text: str) -> tuple[list[ProblemType], str]:
    lowered = text.lower()
    scores = {
        problem_type: sum(lowered.count(keyword.lower()) for keyword in keywords)
        for problem_type, keywords in KEYWORDS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected = [problem_type for problem_type, score in ranked if score > 0][:3]
    if not selected:
        selected = [ProblemType.OPTIMIZATION]
        return selected, "题面缺少显式类型词，暂以目标—约束优化框架作为可检验起点。"
    evidence = ", ".join(
        f"{problem_type.value}:{scores[problem_type]}" for problem_type in selected
    )
    return selected, f"基于题面目标与关键词命中进行初筛（{evidence}），仍需结合数据校验。"


def retrieve_modeling_knowledge(
    store: KnowledgeStore, query: str, limit: int = 8
) -> list[EvidenceCitation]:
    return store.search(query, limit=limit)


def recommend_candidate_models(problem_types: Iterable[ProblemType]) -> list[CandidateModel]:
    models: list[CandidateModel] = []
    seen: set[str] = set()
    for problem_type in problem_types:
        for model in MODEL_LIBRARY[problem_type]:
            if model.name not in seen:
                models.append(model)
                seen.add(model.name)
    return models[:4]


def validate_analysis_plan(
    *, candidates: list[CandidateModel], citations: list[EvidenceCitation], workflow: list[str]
) -> list[str]:
    issues = []
    if len(candidates) < 2:
        issues.append("候选模型不足两个")
    if not citations:
        issues.append("知识检索没有返回可追溯引用")
    if len(workflow) < 4:
        issues.append("求解流程过短")
    return issues


def render_paper_ready(package: PaperReadyPackage) -> str:
    lines = [
        "[PAPER_READY]",
        "",
        "## 问题摘要",
        package.problem_summary,
        "",
        "## 子问题",
    ]
    lines.extend(f"- {item}" for item in package.subproblems)
    lines.extend(["", "## 假设"])
    lines.extend(f"- {item}" for item in package.assumptions)
    lines.extend(["", "## 求解流程"])
    lines.extend(f"{index}. {item}" for index, item in enumerate(package.workflow, 1))
    lines.extend(["", "## 检验计划"])
    lines.extend(f"- {item}" for item in package.validation_plan)
    lines.extend(["", f"状态：`{package.status}`"])
    return "\n".join(lines)
