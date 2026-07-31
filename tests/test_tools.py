from __future__ import annotations

import pytest

from modeling_agent.schemas import ProblemType
from modeling_agent.tools import classify_problem, recommend_candidate_models


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("根据历史销量预测未来需求趋势", ProblemType.FORECASTING),
        ("根据带标签样本完成分类识别", ProblemType.CLASSIFICATION),
        ("建立指标体系并对方案综合评价排名", ProblemType.EVALUATION),
        ("在容量约束下寻找成本最小的最优调度", ProblemType.OPTIMIZATION),
        ("建立微分方程描述传热机理", ProblemType.MECHANISTIC),
        ("使用回归和显著性检验分析相关性", ProblemType.STATISTICAL),
        ("分析网络节点和最短路", ProblemType.NETWORK),
        ("使用聚类发现相似群体", ProblemType.CLUSTERING),
        ("研究竞争主体的纳什博弈策略", ProblemType.GAME_THEORY),
        ("评估污染对生态环境和种群的影响", ProblemType.ECOLOGICAL),
        ("建立坐标系计算运动轨迹和碰撞", ProblemType.GEOMETRIC),
        ("利用蒙特卡洛仿真排队过程", ProblemType.SIMULATION),
    ],
)
def test_problem_classification(text: str, expected: ProblemType) -> None:
    result, rationale = classify_problem(text)
    assert expected in result
    assert rationale


def test_recommend_at_least_two_models() -> None:
    models = recommend_candidate_models([ProblemType.OPTIMIZATION])
    assert len(models) >= 2
    assert len({model.name for model in models}) == len(models)
