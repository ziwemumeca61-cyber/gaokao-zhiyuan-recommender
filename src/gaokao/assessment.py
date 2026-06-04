"""霍兰德 RIASEC 职业兴趣测评：题库、计分与'适合方向'推断。

每题对应一个兴趣维度，考生用 1~5 表达认同程度；按维度归一化得到 0~1 的兴趣向量，
并据主导类型给出建议的专业门类，帮考生从'我是什么样的人'过渡到'适合哪些专业'。
"""

from __future__ import annotations

from .models import RIASEC_DIMENSIONS, RIASEC_LABELS

# (题干, 维度)
QUESTIONS: list[tuple[str, str]] = [
    ("我喜欢动手操作工具、机器或设备", "R"),
    ("我愿意从事户外或体力型的工作", "R"),
    ("我喜欢修理或组装东西", "R"),
    ("比起空谈，我更看重实际做出来的东西", "R"),
    ("我喜欢钻研问题、寻找事物背后的原理", "I"),
    ("我对科学实验和数据分析很感兴趣", "I"),
    ("我喜欢阅读和思考抽象的理论", "I"),
    ("遇到难题我会享受拆解和探究的过程", "I"),
    ("我喜欢用文字、绘画、音乐等方式表达自己", "A"),
    ("我富有想象力，喜欢有创意的事物", "A"),
    ("我不喜欢一成不变、按部就班的工作", "A"),
    ("我欣赏艺术、设计和美的事物", "A"),
    ("我乐于帮助和关心他人", "S"),
    ("我喜欢与人交流、倾听别人的想法", "S"),
    ("我擅长教别人或向他人讲解", "S"),
    ("做对他人有益的事让我有成就感", "S"),
    ("我喜欢带领团队、说服和影响他人", "E"),
    ("我有进取心，喜欢竞争和挑战", "E"),
    ("我对创业、经营或销售感兴趣", "E"),
    ("我愿意为达成目标主动承担责任", "E"),
    ("我做事细致、注重条理和规则", "C"),
    ("我喜欢和数字、表格、流程打交道", "C"),
    ("我倾向于在稳定、有秩序的环境中工作", "C"),
    ("我会把资料和事务整理得井井有条", "C"),
]

# 主导兴趣类型 -> 建议专业门类
TYPE_TO_CATEGORIES: dict[str, list[str]] = {
    "R": ["工学", "农学"],
    "I": ["理学", "工学", "医学"],
    "A": ["艺术学", "文学"],
    "S": ["教育学", "医学", "法学"],
    "E": ["管理学", "经济学"],
    "C": ["管理学", "经济学"],
}

LIKERT_MAX = 5


def score(answers: dict[int, int]) -> dict[str, float]:
    """answers: {题目索引: 1~5}。返回各维度 0~1 的归一化分。"""
    totals = {d: 0.0 for d in RIASEC_DIMENSIONS}
    counts = {d: 0 for d in RIASEC_DIMENSIONS}
    for idx, (_, dim) in enumerate(QUESTIONS):
        val = answers.get(idx)
        if val is None:
            continue
        totals[dim] += val
        counts[dim] += 1
    return {
        d: round(totals[d] / (counts[d] * LIKERT_MAX), 4) if counts[d] else 0.0
        for d in RIASEC_DIMENSIONS
    }


def top_types(riasec: dict[str, float], n: int = 2) -> list[str]:
    ordered = sorted(RIASEC_DIMENSIONS, key=lambda d: riasec.get(d, 0.0), reverse=True)
    return ordered[:n]


def suggested_categories(riasec: dict[str, float], n_types: int = 2) -> list[str]:
    cats: list[str] = []
    for t in top_types(riasec, n_types):
        for c in TYPE_TO_CATEGORIES.get(t, []):
            if c not in cats:
                cats.append(c)
    return cats


def describe_types(riasec: dict[str, float], n: int = 2) -> str:
    types = top_types(riasec, n)
    return " + ".join(f"{t}({RIASEC_LABELS[t]})" for t in types)
