"""精度回归守门：用留出法回测，断言推荐准确度不低于基线，防止改动悄悄降低质量。

针对**真实历史数据**（data/real，含 2025）；缺失时跳过。conftest 把默认数据指向
模拟数据，故此处显式传入 data/real。取几个大样本省（经分区文件加载，快）。
"""

from pathlib import Path

import pytest

from gaokao.data_loader import data_available
from gaokao.recommender.backtest import run_backtest

_REAL = Path(__file__).resolve().parents[1] / "data" / "real"
# 取历年样本充足的大省，经 admissions/{省}.csv.gz 分区快速加载
_PROVINCES = ["河南", "四川", "山东", "河北"]


@pytest.fixture(scope="module")
def metrics():
    if not data_available(str(_REAL)):
        pytest.skip("无 data/real 真实数据，跳过精度回归")
    m = run_backtest(provinces=_PROVINCES, data_dir=str(_REAL))
    if m.get("n_groups", 0) < 5000:
        pytest.skip(f"真实历史数据不足（n={m.get('n_groups', 0)}），跳过精度回归")
    return m


def test_line_prediction_accuracy(metrics):
    """位次线预测：中位相对误差不超过 15%，±20% 命中不低于 70%。"""
    assert metrics["line_median_rel"] <= 0.15, metrics["line_median_rel"]
    assert metrics["line_within20"] >= 0.70, metrics["line_within20"]


def test_probability_calibration(metrics):
    """录取概率校准：平均校准误差不超过 8%（预测概率应接近实际录取率）。"""
    assert metrics["calib_error"] <= 0.08, metrics["calib_error"]


def test_probability_monotonic_calibration(metrics):
    """单调性：高预测概率档的实际录取率应高于低档（冲稳保排序可信的底线）。"""
    buckets = metrics["buckets"]
    low = buckets.get(2)   # 20-30%
    high = buckets.get(7)  # 70-80%
    if low and high:
        assert high[2] > low[2], (low[2], high[2])
