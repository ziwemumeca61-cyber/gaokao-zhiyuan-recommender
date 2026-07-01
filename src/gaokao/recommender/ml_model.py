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
# σ 标定自留出法回测（用 ≤2024 预测 2025）：对数位次预测残差的真实标准差≈0.24。
# 旧值（base0.22/plan1.0/trend0.6）使平均 σ≈0.74、概率被压向 50%，校准误差达 19%；
# 现降到与真实波动相当，校准误差降至约 4%。详见 scripts/backtest.py。
_BASE_SIGMA = 0.20   # 历史波动信息不足时的先验/下限（对数位次）
_PLAN_SIGMA = 0.15   # 招生计划越少略增不确定性（小项，避免主导）
_TREND_SIGMA = 0.4   # 近年趋势越陡（大小年），不确定性越大
_DEFAULT_SIGMA = 0.22


def _phi(x: float) -> float:
    """标准正态分布累积函数 Φ。"""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _sigma(rank_cv: float, years: int, plan: int, trend: float = 0.0) -> float:
    """估计录取线在对数位次上的波动 σ：历史波动(下限 _BASE_SIGMA) + 计划 + 趋势。"""
    hist = rank_cv if years >= 2 else _BASE_SIGMA
    hist = max(hist, _BASE_SIGMA)
    plan_term = _PLAN_SIGMA / math.sqrt(max(plan, 1))
    trend_term = _TREND_SIGMA * abs(trend)
    return math.sqrt(hist * hist + plan_term * plan_term + trend_term * trend_term)


def predict_prob(student_rank: int, ref_rank: int, sigma: float = _DEFAULT_SIGMA) -> float:
    """录取概率 = Φ( ln(ref/student) / σ )，夹到 [0.01, 0.99]（不承诺绝对录取/落榜）。"""
    d = math.log((ref_rank + 1) / (student_rank + 1))
    return round(min(0.99, max(0.01, _phi(d / max(sigma, 1e-6)))), 4)


def _proj_ref(ref_rank: int, plan_ratio: float) -> int:
    """投影参考位次。

    注：曾按 plan_ratio 修正(扩招→线走低)，但留出法回测显示——分省分专业的招生计划
    多为个位数、其年度比值噪声极大——该修正反而使位次预测变差(中位 9.8%→13.2%)，
    故不再据此平移参考线；plan_ratio 仅用于不确定性(σ)与文案提示。"""
    return max(1, ref_rank)


def predict_intervals(
    student_rank: int,
    candidates: list[tuple],
) -> list[tuple[float, float, float]]:
    """批量返回 (点估计, 下界, 上界)。

    candidates 每项 (ref_rank, trend, rank_cv, years, plan[, plan_ratio])。区间反映
    "参考位次估计"的不确定性：以标准误 se=σ/√years 扰动 ref，得到概率上下界。
    """
    out: list[tuple[float, float, float]] = []
    for cand in candidates:
        ref, trend, rank_cv, years, plan = cand[:5]
        plan_ratio = cand[5] if len(cand) > 5 else 1.0
        sig = _sigma(rank_cv, years, plan, trend)
        se = sig / math.sqrt(max(years, 1))
        pref = _proj_ref(ref, plan_ratio)
        p = predict_prob(student_rank, pref, sig)
        hi = predict_prob(student_rank, max(1, round(pref * math.exp(se))), sig)
        lo = predict_prob(student_rank, max(1, round(pref * math.exp(-se))), sig)
        out.append((p, min(lo, hi), max(lo, hi)))
    return out


def predict_interval(
    student_rank: int, ref_rank: int, trend: float = 0.0, *,
    rank_cv: float = 0.0, years: int = 1, plan: int = 1, plan_ratio: float = 1.0,
    z: float = 1.0,
) -> tuple[float, float, float]:
    """单候选版（compare 页与测试使用）。"""
    return predict_intervals(
        student_rank, [(ref_rank, trend, rank_cv, years, plan, plan_ratio)])[0]


def confidence_label(rank_cv: float, years: int, trend: float = 0.0) -> str:
    """把握度 = 对该专业录取线预测的**可靠度**，取决于历史年数与录取线波动，
    与考生处在冲/稳/保无关（避免"稳但把握度低"的困惑）。

    年份足、线稳 → 高；只有一年或波动/大小年明显 → 低。
    """
    if years <= 1:
        return "低"
    vol = math.sqrt(rank_cv * rank_cv + (0.6 * abs(trend)) ** 2)
    if years >= 3 and vol <= 0.18:
        return "高"
    if vol <= 0.35:
        return "中"
    return "低"


def _confidence_by_width(low: float, high: float) -> str:
    """（旧）按概率区间宽度给把握度，保留备用。"""
    width = high - low
    if width <= 0.18:
        return "高"
    if width <= 0.38:
        return "中"
    return "低"
