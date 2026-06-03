"""核心数据模型。

用 dataclass 描述系统的领域对象：考生、院校、专业、历年录取记录、推荐结果。
RIASEC 指霍兰德职业兴趣的六个维度：
R(现实型) I(研究型) A(艺术型) S(社会型) E(企业型) C(常规型)。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 霍兰德六维度（保持顺序固定，向量化时按此顺序）
RIASEC_DIMENSIONS: tuple[str, ...] = ("R", "I", "A", "S", "E", "C")
RIASEC_LABELS: dict[str, str] = {
    "R": "现实型",
    "I": "研究型",
    "A": "艺术型",
    "S": "社会型",
    "E": "企业型",
    "C": "常规型",
}

# 推荐档位
TIER_RUSH = "冲"
TIER_STABLE = "稳"
TIER_SAFE = "保"
TIERS: tuple[str, ...] = (TIER_RUSH, TIER_STABLE, TIER_SAFE)


@dataclass
class Student:
    """考生画像。riasec 为 0~1 的六维兴趣向量（未测评时全 0）。"""

    score: float
    rank: int
    province: str
    subject_type: str  # "物理" 或 "历史"
    riasec: dict[str, float] = field(default_factory=lambda: {d: 0.0 for d in RIASEC_DIMENSIONS})
    city_prefs: list[str] = field(default_factory=list)
    major_prefs: list[str] = field(default_factory=list)  # 偏好的专业门类
    level_pref: str | None = None  # 偏好院校层次，如 "985"/"211"/"双一流"/None

    def riasec_vector(self) -> list[float]:
        return [float(self.riasec.get(d, 0.0)) for d in RIASEC_DIMENSIONS]

    def has_assessment(self) -> bool:
        return any(v > 0 for v in self.riasec.values())


@dataclass
class School:
    """院校。level 如 985/211/双一流/普通；type 如 综合/理工/师范。"""

    id: str
    name: str
    province: str
    city: str
    level: str
    type: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Major:
    """专业，含科普字段，用于让学生'看懂'专业。"""

    id: str
    name: str
    category: str  # 学科门类，如 工学/理学/经济学
    school_id: str
    riasec_code: str  # 主导兴趣类型，如 "IR"（取前若干主导维度）
    heat: float  # 热度 0~100
    employment_rate: float  # 就业率 0~1
    # 科普字段
    intro: str = ""
    core_courses: list[str] = field(default_factory=list)
    career_paths: list[str] = field(default_factory=list)
    industry_outlook: str = ""
    suits: str = ""


@dataclass
class AdmissionRecord:
    """某院校某专业在某省某科类某年的录取情况。"""

    school_id: str
    major_id: str
    year: int
    province: str
    subject_type: str
    min_score: int
    min_rank: int
    plan_count: int


@dataclass
class Recommendation:
    """单条志愿推荐结果。"""

    school: School
    major: Major
    tier: str  # 冲/稳/保
    probability: float  # 录取概率 0~1
    interest_match: float  # 兴趣匹配度 0~1
    composite_score: float  # 综合排序分 0~1
    ref_rank: int  # 参考录取位次（近年加权）
    ref_score: int  # 参考录取分数
    reasons: list[str] = field(default_factory=list)
