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
