"""兴趣偏好匹配：把考生 RIASEC 六维向量与专业主导兴趣码做相似度。

专业的 riasec_code 是若干主导维度的字母组合（如 "IR"），转成 0/1 加权向量后与考生
向量做余弦相似度，得到 0~1 的兴趣匹配度。
"""

from __future__ import annotations

import math

from ..models import RIASEC_DIMENSIONS


def code_to_vector(code: str) -> list[float]:
    """专业兴趣码 -> 六维向量，靠前的主导维度权重更高。"""
    weights = {}
    for i, ch in enumerate(code.upper()):
        if ch in RIASEC_DIMENSIONS and ch not in weights:
            weights[ch] = 1.0 - 0.3 * i  # 第一个 1.0，第二个 0.7 ...
    return [weights.get(d, 0.0) for d in RIASEC_DIMENSIONS]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def match(student_riasec: dict[str, float], major_code: str) -> float:
    """0~1 的兴趣匹配度；考生未测评（全 0）时返回中性值 0.5。"""
    student_vec = [float(student_riasec.get(d, 0.0)) for d in RIASEC_DIMENSIONS]
    if not any(v > 0 for v in student_vec):
        return 0.5
    return round(_cosine(student_vec, code_to_vector(major_code)), 4)
