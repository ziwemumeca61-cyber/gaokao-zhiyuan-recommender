"""多维综合加权评分：把录取概率、兴趣匹配、城市/层次/门类偏好、专业热度
归一化后加权求和，得到用于组内排序的 composite_score（0~1）。权重可配置。
"""

from __future__ import annotations

from ..models import Major, School, Student

# 默认权重（和为 1）。注：真实数据缺就业率，故不纳入综合分。
DEFAULT_WEIGHTS: dict[str, float] = {
    "probability": 0.40,
    "interest": 0.26,
    "heat": 0.10,
    "city": 0.10,
    "level": 0.08,
    "category": 0.06,
}


def _city_score(student: Student, school: School) -> float:
    if not student.city_prefs:
        return 0.6
    return 1.0 if (school.city in student.city_prefs or
                   school.province in student.city_prefs) else 0.3


def _level_score(student: Student, school: School) -> float:
    if not student.level_pref:
        return 0.6
    if school.level == student.level_pref:
        return 1.0
    if student.level_pref == "211" and school.level == "985":
        return 1.0  # 985 满足 211 偏好
    return 0.4


def _category_score(student: Student, major: Major) -> float:
    if not student.major_prefs:
        return 0.6
    return 1.0 if major.category in student.major_prefs else 0.4


def composite(
    student: Student, school: School, major: Major,
    probability: float, interest_match: float,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    parts = {
        "probability": probability,
        "interest": interest_match,
        "heat": major.heat / 100.0,
        "city": _city_score(student, school),
        "level": _level_score(student, school),
        "category": _category_score(student, major),
    }
    score = sum(parts[k] * w.get(k, 0.0) for k in parts)
    return round(score, 4)
