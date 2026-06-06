"""霍兰德 RIASEC 职业兴趣测评：情景二选一题库、计分与'适合方向'推断。

15 道情景题，每题给两个选项、各对应一个兴趣维度（六维两两配对，覆盖全部组合）。
考生每题选"更像自己"的那个；按各维度被选中的比例得到 0~1 的兴趣向量，再据主导
类型给出建议的专业门类，帮考生从'我是什么样的人'过渡到'适合哪些专业'。
"""

from __future__ import annotations

from .models import RIASEC_DIMENSIONS, RIASEC_LABELS

# 情景二选一：(选项A, A维度, 选项B, B维度)。六维 C(6,2)=15 种两两配对，均衡覆盖。
SCENARIOS: list[tuple[str, str, str, str]] = [
    ("动手拆装、修理一台设备，弄懂它怎么运转", "R", "钻研一道难题，搞清楚背后的原理", "I"),
    ("亲手做出一个实物或模型", "R", "画画、写作或做点设计", "A"),
    ("在户外动手干活、操作工具", "R", "陪伴、帮助身边需要帮助的人", "S"),
    ("自己埋头把东西做出来", "R", "牵头组织大家一起干一件事", "E"),
    ("动手组装、操作机器", "R", "把资料、账目整理得井井有条", "C"),
    ("分析数据、研究'为什么会这样'", "I", "天马行空地搞创作", "A"),
    ("独自钻研一个问题直到想通", "I", "给别人把难点讲明白、帮人答疑", "S"),
    ("把一个问题深入分析透彻", "I", "说服别人、推动一件事落地", "E"),
    ("探究事物背后的原理", "I", "按既定流程把事情做规范", "C"),
    ("用作品表达自己的想法", "A", "关心、照顾需要帮助的人", "S"),
    ("自由创作、不受拘束", "A", "经营、销售、影响他人", "E"),
    ("凭灵感、不拘一格地做事", "A", "讲条理、按规则一步步来", "C"),
    ("默默倾听、帮助他人", "S", "带领团队、说服众人", "E"),
    ("多和人打交道、帮人解决事情", "S", "多和数字、表格、流程打交道", "C"),
    ("带头去闯、争第一", "E", "稳妥细致、守规则不出错", "C"),
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


def score(answers: dict[int, str]) -> dict[str, float]:
    """answers: {题目索引: 所选维度字母}。返回各维度 0~1 的得分（被选比例）。"""
    chosen = {d: 0 for d in RIASEC_DIMENSIONS}
    appeared = {d: 0 for d in RIASEC_DIMENSIONS}
    for idx, (_a, dim_a, _b, dim_b) in enumerate(SCENARIOS):
        pick = answers.get(idx)
        if pick is None:
            continue
        appeared[dim_a] += 1
        appeared[dim_b] += 1
        if pick in (dim_a, dim_b):
            chosen[pick] += 1
    return {
        d: round(chosen[d] / appeared[d], 4) if appeared[d] else 0.0
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
