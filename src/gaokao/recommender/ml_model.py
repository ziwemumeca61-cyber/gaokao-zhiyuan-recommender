"""录取概率预测（基于真实历史波动校准）。

把"明年录取最低位次"建模为对数正态：中位数≈参考位次 ref，波动 σ 来自该专业历年
录取位次的真实波动（再按可用年份/招生计划/趋势做小样本与稳定性修正）。考生位次 r 被
录取的概率 = P(明年录取线位次 ≥ r) = Φ( ln(ref/r) / σ )，Φ 为标准正态分布函数。

直觉：你的位次比参考线越靠前，概率越高；该专业历年越不稳定（σ 越大），概率越向 50%
回归、区间越宽。纯数学实现，无需任何机器学习依赖。
"""

from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)
_BASE_SIGMA = 0.22   # 缺历史波动信息时的先验相对波动（对数位次）
_PLAN_SIGMA = 1.0    # 招生计划越少，录取线越不稳定
_TREND_SIGMA = 0.6   # 近年趋势越陡（大小年），不确定性越大
_DEFAULT_SIGMA = 0.35


def _phi(x: float) -> float:
    """标准正态分布累积函数 Φ。"""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _sigma(rank_cv: float, years: int, plan: int, trend: float = 0.0) -> float:
    """估计录取线在对数位次上的波动 σ：历史波动 + 小样本膨胀 + 计划 + 趋势。"""
    hist = rank_cv if years >= 2 else _BASE_SIGMA
    hist = max(hist, _BASE_SIGMA / math.sqrt(max(years, 1)))
    plan_term = _PLAN_SIGMA / math.sqrt(max(plan, 1))
    trend_term = _TREND_SIGMA * abs(trend)
    return math.sqrt(hist * hist + plan_term * plan_term + trend_term * trend_term)


def predict_prob(student_rank: int, ref_rank: int, sigma: float = _DEFAULT_SIGMA) -> float:
    """录取概率 = Φ( ln(ref/student) / σ )，夹到 [0.01, 0.99]（不承诺绝对录取/落榜）。"""
    d = math.log((ref_rank + 1) / (student_rank + 1))
    return round(min(0.99, max(0.01, _phi(d / max(sigma, 1e-6)))), 4)


def predict_intervals(
    student_rank: int,
    candidates: list[tuple[int, float, float, int, int]],
) -> list[tuple[float, float, float]]:
    """批量返回 (点估计, 下界, 上界)。

    candidates 每项 (ref_rank, trend, rank_cv, years, plan)。区间反映"参考位次估计"的
    不确定性：以标准误 se=σ/√years 扰动 ref，得到概率上下界。
    """
    out: list[tuple[float, float, float]] = []
    for ref, trend, rank_cv, years, plan in candidates:
        sig = _sigma(rank_cv, years, plan, trend)
        se = sig / math.sqrt(max(years, 1))
        p = predict_prob(student_rank, ref, sig)
        hi = predict_prob(student_rank, max(1, round(ref * math.exp(se))), sig)
        lo = predict_prob(student_rank, max(1, round(ref * math.exp(-se))), sig)
        out.append((p, min(lo, hi), max(lo, hi)))
    return out


def predict_interval(
    student_rank: int, ref_rank: int, trend: float = 0.0, *,
    rank_cv: float = 0.0, years: int = 1, plan: int = 1, z: float = 1.0,
) -> tuple[float, float, float]:
    """单候选版（compare 页与测试使用）。"""
    return predict_intervals(student_rank, [(ref_rank, trend, rank_cv, years, plan)])[0]


def confidence_label(low: float, high: float) -> str:
    """按区间宽度给"把握度"标签：越窄越有把握。"""
    width = high - low
    if width <= 0.18:
        return "高"
    if width <= 0.38:
        return "中"
    return "低"
