"""推荐引擎：编排冲稳保位次法、兴趣匹配、ML 概率预测、综合评分，产出统一志愿表。"""

from __future__ import annotations

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

    for (school_id, major_id), stat in stats.items():
        school = schools.get(school_id)
        major = majors.get(major_id)
        if school is None or major is None:
            continue
        tier = rank_based.classify(student.rank, stat.ref_rank)
        if tier is None:
            continue

        probability, prob_low, prob_high = ml_model.predict_interval(
            student.rank, stat.ref_rank, stat.trend,
            rank_cv=stat.rank_cv, years=stat.years, plan=stat.total_plan)
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
    if major.employment_rate >= 0.88:
        reasons.append(f"就业率较高（{major.employment_rate * 100:.0f}%）")
    if student.level_pref and school.level == student.level_pref:
        reasons.append(f"符合你偏好的院校层次（{school.level}）")
    if stat.trend > 0.06:
        reasons.append("近年报考热度上升，注意竞争加剧")
    return reasons
