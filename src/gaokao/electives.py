"""选科要求解析与匹配。

把专业的"选科要求"原文解析成可判定的规则，再与考生选考科目比对，判断能否报考。
支持的常见表述：
  不限 / 物理必选 / 物理、化学(2科必选) / 物化生(3科必选)
  物/化/生(3选1) / 物理/化学(2选1) / 历史/地理(2选1)
"""

from __future__ import annotations

# 六门选考科目（标准名）
ELECTIVE_SUBJECTS: tuple[str, ...] = ("物理", "化学", "生物", "政治", "历史", "地理")

# 缩写单字 -> 标准名
_ABBR: dict[str, str] = {
    "物": "物理", "化": "化学", "生": "生物",
    "政": "政治", "史": "历史", "地": "地理",
}
# 全称（含别名），按长度优先匹配，避免"政治"被"治"等误伤
_FULL: list[tuple[str, str]] = [
    ("思想政治", "政治"), ("物理", "物理"), ("化学", "化学"), ("生物", "生物"),
    ("政治", "政治"), ("历史", "历史"), ("地理", "地理"),
]
_NONE_TOKENS = {"", "不限", "none", "nan", "无", "不提科目要求"}


def _extract_subjects(head: str) -> list[str]:
    found: list[str] = []
    tmp = head
    for name, canon in _FULL:          # 先全称
        if name in tmp:
            if canon not in found:
                found.append(canon)
            tmp = tmp.replace(name, "")
    for ch in tmp:                      # 再缩写单字
        canon = _ABBR.get(ch)
        if canon and canon not in found:
            found.append(canon)
    return found


def parse_requirement(text: str | None) -> tuple[str, list[str]]:
    """解析选科要求原文。返回 (mode, subjects)，mode ∈ {'none','all','any'}。"""
    s = str(text or "").strip()
    if s.lower() in _NONE_TOKENS:
        return ("none", [])
    head = s.split("(")[0].split("（")[0]
    subjects = _extract_subjects(head)
    if not subjects:
        return ("none", [])
    is_any = ("选1" in s) or ("选一" in s) or ("任选" in s)
    return ("any", subjects) if is_any else ("all", subjects)


def satisfies(req_text: str | None, electives: list[str] | set[str]) -> bool:
    """考生选考科目能否满足该选科要求。electives 为空（未填）时视为满足（不过滤）。"""
    mode, subs = parse_requirement(req_text)
    if mode == "none":
        return True
    if not electives:
        return True  # 未提供选考科目，不做过滤
    es = set(electives)
    if mode == "all":
        return all(x in es for x in subs)
    return any(x in es for x in subs)


def requirement_label(text: str | None) -> str:
    """给界面用的简短可读标签。"""
    mode, subs = parse_requirement(text)
    if mode == "none":
        return "选科不限"
    if mode == "all":
        return "需选 " + "、".join(subs) + ("（全选）" if len(subs) > 1 else "")
    return "需选 " + "/".join(subs) + " 任一"
