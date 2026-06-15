"""推荐引擎：编排冲稳保位次法、兴趣匹配、ML 概率预测、综合评分，产出统一志愿表。"""

from __future__ import annotations

from .. import electives
from ..data_loader import load_admissions, load_majors, load_schools
from ..models import TIERS, Recommendation, Student
from . import interest, ml_model, rank_based, scoring
from .history import aggregate


def recommend(
    student: Student,
    data_dir: str | None = None,
    per_tier: int = 10,
    weights: dict[str, float] | None = None,
) -> dict[str, list[Recommendation]]:
    """返回按 冲/稳/保 分组、组内按综合分降序的推荐结果。"""
    schools = load_schools(data_dir)
    majors = load_majors(data_dir)
    admissions = load_admissions(data_dir)

    stats = aggregate(admissions, student.province, student.subject_type)
    buckets: dict[str, list[Recommendation]] = {t: [] for t in TIERS}

    # 第一遍：筛出冲稳保区间内、且满足选科要求的候选（概率稍后批量计算）
    picked: list[tuple] = []  # (tier, school, major, stat)
    for (school_id, major_id), stat in stats.items():
        school = schools.get(school_id)
        major = majors.get(major_id)
        if school is None or major is None:
            continue
        # 选科要求过滤：考生选考科目不满足则不可报，直接剔除
        if not electives.satisfies(major.subject_req, student.electives):
            continue
        tier = rank_based.classify(student.rank, stat.ref_rank)
        if tier is None:
            continue
        picked.append((tier, school, major, stat))

    # 批量计算录取概率区间（基于历年位次波动的正态校准 + 招生计划变化修正）
    intervals = ml_model.predict_intervals(
        student.rank,
        [(s.ref_rank, s.trend, s.rank_cv, s.years, s.total_plan, s.plan_ratio)
         for (_, _, _, s) in picked])

    for (tier, school, major, stat), (probability, prob_low, prob_high) in zip(
            picked, intervals):
        confidence = ml_model.confidence_label(prob_low, prob_high)
        interest_match = interest.match(student.riasec, major.riasec_code)
        composite = scoring.composite(
            student, school, major, probability, interest_match, weights)
        reasons = _build_reasons(student, school, major, stat, tier,
                                 probability, prob_low, prob_high, confidence,
                                 interest_match)
        buckets[tier].append(Recommendation(
            school=school, major=major, tier=tier, probability=probability,
            interest_match=interest_match, composite_score=composite,
            ref_rank=stat.ref_rank, ref_score=stat.ref_score, reasons=reasons,
            prob_low=prob_low, prob_high=prob_high, confidence=confidence,
        ))

    for tier in TIERS:
        buckets[tier].sort(key=lambda r: r.composite_score, reverse=True)
        buckets[tier] = buckets[tier][:per_tier]
    return buckets


def _build_reasons(student, school, major, stat, tier, probability,
                   prob_low, prob_high, confidence, interest_match):
    reasons: list[str] = []
    r = rank_based.ratio(student.rank, stat.ref_rank)
    if tier == "冲":
        reasons.append(f"院校近年位次约 {stat.ref_rank}，略高于你（位次比 {r:.2f}），可冲一冲")
    elif tier == "稳":
        reasons.append(f"院校近年位次约 {stat.ref_rank}，与你位次相近（{r:.2f}），较稳妥")
    else:
        reasons.append(f"院校近年位次约 {stat.ref_rank}，你有明显优势（{r:.2f}），适合保底")

    reasons.append(
        f"模型预测录取概率约 {probability * 100:.0f}%"
        f"（区间 {prob_low * 100:.0f}%–{prob_high * 100:.0f}%，把握度{confidence}）")

    if student.has_assessment():
        if interest_match >= 0.7:
            reasons.append(f"与你的兴趣高度契合（匹配度 {interest_match:.2f}）")
        elif interest_match >= 0.4:
            reasons.append(f"与你的兴趣较为契合（匹配度 {interest_match:.2f}）")
    if student.level_pref and school.level == student.level_pref:
        reasons.append(f"符合你偏好的院校层次（{school.level}）")
    if stat.rank_cv >= 0.25:
        reasons.append("近年录取位次波动较大（疑似大小年），录取概率不确定性偏高")
    elif stat.trend > 0.10:
        reasons.append("近年录取位次走高、竞争加剧，注意风险")
    if stat.plan_ratio >= 1.2:
        reasons.append(f"近一年招生计划明显多于前几年（约 {stat.plan_ratio:.1f} 倍），录取线或有走低趋势")
    elif stat.plan_ratio <= 0.8:
        reasons.append("近一年招生计划较前几年减少，录取线或走高，需谨慎")
    return reasons
