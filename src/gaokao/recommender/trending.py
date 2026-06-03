"""热门专业推荐。

把同名专业跨院校聚合，按 综合热度 = 热度 + 就业率 + 开设广度 排出热门榜；
个性化版可与引擎产出的推荐取交集，只保留"分数够得着的热门专业"。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..models import Major

# 综合热度权重
_W_HEAT = 0.55
_W_EMPLOY = 0.30
_W_BREADTH = 0.15


@dataclass
class MajorTrend:
    name: str
    category: str
    avg_heat: float
    avg_employment: float
    count: int          # 开设该专业的院校数（广度）
    score: float        # 综合热度 0~100
    sample: Major       # 代表性专业对象（用于跳转科普）


def rank_hot_majors(
    majors: dict[str, Major], category: str | None = None, top_n: int = 20
) -> list[MajorTrend]:
    grouped: dict[str, list[Major]] = defaultdict(list)
    for m in majors.values():
        if category and m.category != category:
            continue
        grouped[m.name].append(m)
    if not grouped:
        return []

    max_count = max(len(v) for v in grouped.values())
    trends: list[MajorTrend] = []
    for name, items in grouped.items():
        avg_heat = sum(m.heat for m in items) / len(items)
        avg_emp = sum(m.employment_rate for m in items) / len(items)
        breadth = len(items) / max_count
        score = (_W_HEAT * avg_heat
                 + _W_EMPLOY * avg_emp * 100
                 + _W_BREADTH * breadth * 100)
        trends.append(MajorTrend(
            name=name, category=items[0].category, avg_heat=round(avg_heat, 1),
            avg_employment=round(avg_emp, 3), count=len(items),
            score=round(score, 1), sample=items[0],
        ))
    trends.sort(key=lambda t: t.score, reverse=True)
    return trends[:top_n]


def hot_major_names(majors: dict[str, Major], top_n: int = 20) -> set[str]:
    return {t.name for t in rank_hot_majors(majors, top_n=top_n)}
