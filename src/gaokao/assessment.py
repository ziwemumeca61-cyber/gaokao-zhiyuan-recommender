"""霍兰德 RIASEC 职业兴趣测评：情景二选一题库、计分与'适合方向'推断。

15 道情景题，每题给两个选项、各对应一个兴趣维度（六维两两配对，覆盖全部组合）。
考生每题选"更像自己"的那个；按各维度被选中的比例得到 0~1 的兴趣向量，再据主导
类型给出建议的专业门类，帮考生从'我是什么样的人'过渡到'适合哪些专业'。
"""

from __future__ import annotations

from .models import RIASEC_DIMENSIONS, RIASEC_LABELS

# 情景二选一：(情景引子, 选项A, A维度, 选项B, B维度)。六维 C(6,2)=15 种两两配对。
SCENARIOS: list[tuple[str, str, str, str, str]] = [
    ("电脑突然卡死了，你更想——", "动手捣鼓把它弄好", "R", "搞懂它到底为什么会卡", "I"),
    ("周末有空，你更想去——", "打球、动手做点东西", "R", "画画、剪视频或写点东西", "A"),
    ("同学遇到难处，你更愿意——", "帮TA修好/搬好东西", "R", "坐下来听TA倾诉、安慰TA", "S"),
    ("小组作业，你更可能——", "自己埋头把活儿做出来", "R", "当组长，安排谁干什么", "E"),
    ("考完试的下午，你更想——", "拆装、鼓捣点设备", "R", "把错题和笔记整理得整整齐齐", "C"),
    ("一道超难的题，你更享受——", "死磕到底、把它想通", "I", "去构思一个有创意的点子", "A"),
    ("你会做这道难题，你更愿意——", "自己一个人攻克它", "I", "讲给同学听、帮TA也学会", "S"),
    ("班会讨论问题，你更想——", "把问题分析得透透的", "I", "说服大家接受你的方案", "E"),
    ("学新知识时，你更在意——", "弄懂'为什么是这样'", "I", "按步骤、照计划稳稳掌握", "C"),
    ("班级办活动，你更想负责——", "设计海报、做宣传视频", "A", "关心照顾同学、当志愿者", "S"),
    ("选社团，你更想加入——", "美术/文学/音乐社自由创作", "A", "学生会，竞选带一群人做事", "E"),
    ("做手抄报，你更倾向——", "天马行空、不拘一格", "A", "排版工整、按规矩来", "C"),
    ("班里要选人，你更适合——", "当大家的知心人、帮同学", "S", "当班长，号召并带着大家", "E"),
    ("找份实践/兼职，你更想——", "多和人打交道、帮到别人", "S", "和数据、表格、流程打交道", "C"),
    ("说到做事风格，你更像——", "带头冲、敢拍板、争第一", "E", "稳妥细致、守规则不出错", "C"),
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
    for idx, (_stem, _a, dim_a, _b, dim_b) in enumerate(SCENARIOS):
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
