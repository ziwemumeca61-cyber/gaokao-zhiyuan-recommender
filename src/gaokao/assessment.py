"""霍兰德 RIASEC 职业兴趣测评：逐句自评题库、计分与'适合方向'推断。

改用更易作答的"逐句打分"：18 句描述、每句只对应一个兴趣维度，考生独立地评
"像我 / 一般 / 不像我"（计 1 / 0.5 / 0 分），无需在两件不相干的事之间硬二选一。
各维度取所属句子的平均分得到 0~1 的兴趣向量，再据主导类型给出建议的专业门类，
帮考生从'我是什么样的人'过渡到'适合哪些专业'。
"""

from __future__ import annotations

from .models import RIASEC_DIMENSIONS, RIASEC_LABELS

# 逐句自评：(描述, 对应维度)。六维各 3 句，按维度轮转排列，作答时不显得扎堆。
STATEMENTS: list[tuple[str, str]] = [
    ("我喜欢动手把东西拆开、修好或组装起来", "R"),
    ("遇到不懂的问题，我会忍不住想弄明白背后的原理", "I"),
    ("我喜欢用画画、写作、音乐或剪辑来表达自己", "A"),
    ("我乐于倾听、安慰和帮助身边的人", "S"),
    ("我喜欢带头组织大家一起把事情做成", "E"),
    ("我做事喜欢有计划、有条理、按步骤来", "C"),
    ("比起纯看书，我更喜欢操作工具、设备或做实验", "R"),
    ("我喜欢钻研难题，享受推理和分析的过程", "I"),
    ("我常冒出新点子，不喜欢一成不变、千篇一律", "A"),
    ("帮别人解决困扰、教会别人，让我很有成就感", "S"),
    ("我愿意去说服别人、争取机会、当负责人", "E"),
    ("我擅长整理资料、表格和流程，追求准确无误", "C"),
    ("户外活动、体育或动手干活让我觉得带劲", "R"),
    ("我对科学、数据和'为什么会这样'特别好奇", "I"),
    ("自由发挥和审美对我很重要，我享受创作的过程", "A"),
    ("我喜欢和人打交道、照顾和服务他人", "S"),
    ("竞争和挑战让我兴奋，我想做出成绩、争第一", "E"),
    ("规则清晰、安排稳妥的环境让我安心", "C"),
]

# 作答档位 -> 分值
RATINGS: list[tuple[str, float]] = [
    ("👍 像我", 1.0),
    ("😐 一般", 0.5),
    ("🙅 不像我", 0.0),
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


def score(answers: dict[int, float]) -> dict[str, float]:
    """answers: {句子索引: 评分(1/0.5/0)}。返回各维度 0~1 的得分（所属句子均分）。

    未作答的句子不计入该维度的平均；某维度全部未答则记 0。
    """
    total = {d: 0.0 for d in RIASEC_DIMENSIONS}
    count = {d: 0 for d in RIASEC_DIMENSIONS}
    for idx, (_text, dim) in enumerate(STATEMENTS):
        val = answers.get(idx)
        if val is None:
            continue
        total[dim] += val
        count[dim] += 1
    return {
        d: round(total[d] / count[d], 4) if count[d] else 0.0
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
