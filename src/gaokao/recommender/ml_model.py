"""录取概率预测。

用合成历史样本训练 scikit-learn 逻辑回归；若没有 sklearn，则退化为等价的
解析式 sigmoid，保证概率预测永远可用。核心特征是考生位次与院校参考位次的对数比值
log(ref_rank / student_rank)：考生位次越靠前（数字更小），录取概率越高。
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

# 解析式兜底的系数
_K_RATIO = 2.6   # 对数位次比的权重
_K_TREND = 0.8   # 竞争趋势的负向影响


def _features(student_rank: int, ref_rank: int, trend: float) -> list[float]:
    ratio = math.log((ref_rank + 1) / (student_rank + 1))
    return [ratio, trend]


def _analytic_prob(student_rank: int, ref_rank: int, trend: float) -> float:
    ratio, tr = _features(student_rank, ref_rank, trend)
    z = _K_RATIO * ratio - _K_TREND * tr
    return 1.0 / (1.0 + math.exp(-z))


@lru_cache(maxsize=1)
def _trained_model():
    """惰性训练逻辑回归；失败则返回 None 触发解析式兜底。"""
    try:
        import numpy as np  # noqa: PLC0415
        from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    except Exception:
        return None

    rng = random.Random(42)
    X, y = [], []
    for _ in range(4000):
        student_rank = rng.randint(100, 200_000)
        ref_rank = rng.randint(100, 200_000)
        trend = rng.uniform(-0.2, 0.2)
        feat = _features(student_rank, ref_rank, trend)
        # 合成标签：解析式概率 + 噪声，门限 0.5
        p = _analytic_prob(student_rank, ref_rank, trend)
        label = 1 if rng.random() < p else 0
        X.append(feat)
        y.append(label)
    model = LogisticRegression()
    model.fit(np.array(X), np.array(y))
    return model


def predict_prob(student_rank: int, ref_rank: int, trend: float = 0.0) -> float:
    """返回 0~1 的录取概率。"""
    model = _trained_model()
    if model is None:
        return round(_analytic_prob(student_rank, ref_rank, trend), 4)
    import numpy as np  # noqa: PLC0415

    feat = np.array([_features(student_rank, ref_rank, trend)])
    return round(float(model.predict_proba(feat)[0][1]), 4)


def _predict_many(feats: list[list[float]]) -> list[float]:
    """批量预测：sklearn 一次性 predict_proba；无 sklearn 时逐行解析式兜底。"""
    if not feats:
        return []
    model = _trained_model()
    if model is None:
        out = []
        for ratio, tr in feats:
            z = _K_RATIO * ratio - _K_TREND * tr
            out.append(round(1.0 / (1.0 + math.exp(-z)), 4))
        return out
    import numpy as np  # noqa: PLC0415

    probs = model.predict_proba(np.array(feats))[:, 1]
    return [round(float(p), 4) for p in probs]


# ---------------------------------------------------------------------------
# 概率校准：用参考位次的不确定性推导录取概率的置信区间
# ---------------------------------------------------------------------------
_BASE_SIGMA = 0.18   # 缺历史波动信息时的先验相对不确定性（对数位次）
_PLAN_SIGMA = 1.0    # 招生计划越少，录取线越不稳定的系数


def _sigma_log_ref(rank_cv: float, years: int, plan: int) -> float:
    """估计参考位次在对数尺度上的标准差，越大表示越不确定。

    三个来源：历史位次波动(rank_cv)、可用年份(小样本膨胀)、招生计划(计划越少越抖)。
    """
    hist = rank_cv if years >= 2 else _BASE_SIGMA
    hist = max(hist, _BASE_SIGMA / math.sqrt(max(years, 1)))
    plan_term = _PLAN_SIGMA / math.sqrt(max(plan, 1))
    return math.sqrt(hist * hist + plan_term * plan_term)


def predict_interval(
    student_rank: int, ref_rank: int, trend: float = 0.0, *,
    rank_cv: float = 0.0, years: int = 1, plan: int = 1, z: float = 1.0,
) -> tuple[float, float, float]:
    """返回 (点估计, 下界, 上界)。

    在对数位次维度上把参考位次按 ±z·σ 扰动，复用同一个预测器求概率端点——
    因此与 sklearn / 解析式兜底都一致，且区间天然落在 [0,1]。
    """
    p = predict_prob(student_rank, ref_rank, trend)
    sigma = _sigma_log_ref(rank_cv, years, plan)
    ref_lo = max(1, round(ref_rank * math.exp(-z * sigma)))
    ref_hi = max(1, round(ref_rank * math.exp(z * sigma)))
    a = predict_prob(student_rank, ref_lo, trend)
    b = predict_prob(student_rank, ref_hi, trend)
    return p, min(a, b), max(a, b)


def predict_intervals(
    student_rank: int,
    candidates: list[tuple[int, float, float, int, int]],
    z: float = 1.0,
) -> list[tuple[float, float, float]]:
    """批量版 predict_interval。

    candidates: 每项 (ref_rank, trend, rank_cv, years, plan)。
    返回与之一一对应的 (点估计, 下界, 上界)。所有候选的点/上/下三点特征拼成一个
    矩阵一次预测，避免逐候选调用 sklearn 的高开销。
    """
    feats: list[list[float]] = []
    for ref, trend, rank_cv, years, plan in candidates:
        sigma = _sigma_log_ref(rank_cv, years, plan)
        ref_lo = max(1, round(ref * math.exp(-z * sigma)))
        ref_hi = max(1, round(ref * math.exp(z * sigma)))
        feats.append(_features(student_rank, ref, trend))
        feats.append(_features(student_rank, ref_lo, trend))
        feats.append(_features(student_rank, ref_hi, trend))
    probs = _predict_many(feats)
    out: list[tuple[float, float, float]] = []
    for i in range(0, len(probs), 3):
        p, a, b = probs[i], probs[i + 1], probs[i + 2]
        out.append((p, min(a, b), max(a, b)))
    return out


def confidence_label(low: float, high: float) -> str:
    """按区间宽度给"把握度"标签：越窄越有把握。"""
    width = high - low
    if width <= 0.18:
        return "高"
    if width <= 0.38:
        return "中"
    return "低"
