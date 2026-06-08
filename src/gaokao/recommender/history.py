"""历年录取记录的聚合工具。

把同一(院校,专业,省份,科类)的多年记录聚合成参考位次/分数与趋势，
供冲稳保分档、概率预测、综合评分共用。
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from ..models import AdmissionRecord

# 近年权重：越近的年份权重越高（最多取最近四年，年份多则估计更稳、波动更可信）
_RECENCY_WEIGHTS = [0.4, 0.3, 0.2, 0.1]


@dataclass
class HistoryStat:
    school_id: str
    major_id: str
    ref_rank: int        # 近年加权参考位次
    ref_score: int       # 近年加权参考分数
    trend: float         # 位次年度变化率（>0 表示位次走高/竞争加剧）
    total_plan: int      # 近一年招生计划数
    years: int           # 可用年份数
    rank_cv: float       # 近年位次的对数波动（标准差），衡量录取线稳定性
    plan_ratio: float    # 最新计划 / 近年平均计划（>1 表示扩招，分数线可能走低）


def aggregate(
    records: list[AdmissionRecord], province: str, subject_type: str
) -> dict[tuple[str, str], HistoryStat]:
    """按(院校,专业)聚合指定省份+科类的历年记录。"""
    grouped: dict[tuple[str, str], list[AdmissionRecord]] = defaultdict(list)
    for r in records:
        if r.province == province and r.subject_type == subject_type:
            grouped[(r.school_id, r.major_id)].append(r)

    stats: dict[tuple[str, str], HistoryStat] = {}
    for key, recs in grouped.items():
        recs.sort(key=lambda r: r.year, reverse=True)
        recent = recs[:4]
        weights = _RECENCY_WEIGHTS[: len(recent)]
        wsum = sum(weights)
        ref_rank = round(sum(r.min_rank * w for r, w in zip(recent, weights)) / wsum)
        ref_score = round(sum(r.min_score * w for r, w in zip(recent, weights)) / wsum)
        trend = _trend(recent)
        plans = [r.plan_count for r in recent if r.plan_count > 0]
        avg_plan = sum(plans) / len(plans) if plans else 0
        plan_ratio = (recent[0].plan_count / avg_plan) if avg_plan > 0 else 1.0
        stats[key] = HistoryStat(
            school_id=key[0], major_id=key[1], ref_rank=ref_rank, ref_score=ref_score,
            trend=trend, total_plan=recent[0].plan_count, years=len(recs),
            rank_cv=_rank_cv(recent), plan_ratio=round(plan_ratio, 3),
        )
    return stats


def _rank_cv(recent: list[AdmissionRecord]) -> float:
    """近年位次在对数尺度上的标准差，作为录取线波动度。单年返回 0。"""
    ranks = [r.min_rank for r in recent if r.min_rank > 0]
    if len(ranks) < 2:
        return 0.0
    logs = [math.log(x) for x in ranks]
    mean = sum(logs) / len(logs)
    var = sum((x - mean) ** 2 for x in logs) / len(logs)
    return math.sqrt(var)


def _trend(recent: list[AdmissionRecord]) -> float:
    """最早到最近的位次相对变化率（位次变小=更难，返回正值）。"""
    if len(recent) < 2:
        return 0.0
    newest, oldest = recent[0].min_rank, recent[-1].min_rank
    if oldest <= 0:
        return 0.0
    # 钳制到 [-0.5, 0.5]：真实数据中个别专业历年位次波动极大，避免趋势主导概率
    return max(-0.5, min(0.5, (oldest - newest) / oldest))
