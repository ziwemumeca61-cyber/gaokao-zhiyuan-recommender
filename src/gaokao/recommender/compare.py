"""院校对比：对任意若干 (院校,专业) 候选，在考生省份+科类口径下算齐可比指标。

与 engine 不同，这里**不做冲稳保过滤**——对比时既要看够不着的冲刺项，也要看稳妥的
保底项。每个候选复用同一套子算法（历史聚合、概率区间、兴趣匹配、综合评分），保证口径
与志愿推荐完全一致。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data_loader import load_majors, load_schools
from ..models import Major, School, Student
from . import interest, ml_model, rank_based, scoring
from .history import aggregate_cached


@dataclass
class CompareRow:
    """单个 (院校,专业) 候选在考生口径下的全部可比指标。"""

    school: School
    major: Major
    has_data: bool          # 该(校,专业)在考生省份+科类下是否有录取数据
    tier: str               # 冲/稳/保，区间外为 ""
    ratio: float            # 位次比 = 考生位次 / 院校位次
    probability: float      # 录取概率点估计 0~1
    prob_low: float
    prob_high: float
    confidence: str         # 把握度 高/中/低
    interest_match: float   # 兴趣匹配 0~1
    composite_score: float  # 综合排序分 0~1
    ref_rank: int           # 参考位次
    ref_score: int          # 参考分数
    trend: float            # 位次趋势（>0 竞争加剧）


def compare(
    student: Student,
    pairs: list[tuple[str, str]],
    data_dir: str | None = None,
    weights: dict[str, float] | None = None,
) -> list[CompareRow]:
    """按给定 (school_id, major_id) 顺序返回对比行；保持入参顺序，跳过无效 id。"""
    schools = load_schools(data_dir)
    majors = load_majors(data_dir)
    stats = aggregate_cached(student.province, student.subject_type, data_dir)

    rows: list[CompareRow] = []
    for school_id, major_id in pairs:
        school = schools.get(school_id)
        major = majors.get(major_id)
        if school is None or major is None:
            continue

        stat = stats.get((school_id, major_id))
        if stat is None:
            # 该省该科类下没有这个专业的录取数据 —— 仍列出，但指标留空
            rows.append(CompareRow(
                school=school, major=major, has_data=False, tier="", ratio=0.0,
                probability=0.0, prob_low=0.0, prob_high=0.0, confidence="",
                interest_match=interest.match(student.riasec, major.riasec_code),
                composite_score=0.0, ref_rank=0, ref_score=0, trend=0.0,
            ))
            continue

        probability, lo, hi = ml_model.predict_interval(
            student.rank, stat.ref_rank, stat.trend,
            rank_cv=stat.rank_cv, years=stat.years, plan=stat.total_plan)
        interest_match = interest.match(student.riasec, major.riasec_code)
        composite = scoring.composite(
            student, school, major, probability, interest_match, weights)
        rows.append(CompareRow(
            school=school, major=major, has_data=True,
            tier=rank_based.classify(student.rank, stat.ref_rank) or "",
            ratio=round(rank_based.ratio(student.rank, stat.ref_rank), 3),
            probability=probability, prob_low=lo, prob_high=hi,
            confidence=ml_model.confidence_label(stat.rank_cv, stat.years, stat.trend),
            interest_match=interest_match, composite_score=composite,
            ref_rank=stat.ref_rank, ref_score=stat.ref_score, trend=stat.trend,
        ))
    return rows


def best_index(rows: list[CompareRow]) -> int | None:
    """综合分最高的候选下标（仅在有数据的候选中选）；都没数据则返回 None。"""
    best, idx = -1.0, None
    for i, r in enumerate(rows):
        if r.has_data and r.composite_score > best:
            best, idx = r.composite_score, i
    return idx
