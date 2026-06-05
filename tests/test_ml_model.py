"""录取概率校准测试：置信区间与把握度。"""

from gaokao.recommender import ml_model


def test_interval_brackets_point_estimate():
    p, lo, hi = ml_model.predict_interval(15000, 16000, years=3, plan=50, rank_cv=0.1)
    assert 0.0 <= lo <= p <= hi <= 1.0


def test_interval_within_unit_range():
    for ref in (500, 5000, 50000, 150000):
        _, lo, hi = ml_model.predict_interval(20000, ref, plan=10)
        assert 0.0 <= lo <= hi <= 1.0


def test_more_years_narrows_interval():
    """同等条件下，年份越多（小样本膨胀越小）区间越窄。"""
    _, lo1, hi1 = ml_model.predict_interval(15000, 16000, years=1, plan=40, rank_cv=0.0)
    _, lo3, hi3 = ml_model.predict_interval(15000, 16000, years=3, plan=40, rank_cv=0.0)
    assert (hi3 - lo3) <= (hi1 - lo1)


def test_larger_plan_narrows_interval():
    """招生计划越大，录取线越稳定，区间越窄。"""
    _, los, his = ml_model.predict_interval(15000, 16000, years=3, plan=5, rank_cv=0.1)
    _, lob, hib = ml_model.predict_interval(15000, 16000, years=3, plan=200, rank_cv=0.1)
    assert (hib - lob) <= (his - los)


def test_higher_volatility_widens_interval():
    _, lol, hil = ml_model.predict_interval(15000, 16000, years=3, plan=40, rank_cv=0.05)
    _, loh, hih = ml_model.predict_interval(15000, 16000, years=3, plan=40, rank_cv=0.6)
    assert (hih - loh) >= (hil - lol)


def test_confidence_label_thresholds():
    assert ml_model.confidence_label(0.50, 0.60) == "高"
    assert ml_model.confidence_label(0.40, 0.70) == "中"
    assert ml_model.confidence_label(0.20, 0.90) == "低"


def test_prob_half_when_rank_equals_ref():
    # 位次正好等于参考线 -> 概率约 50%（正态 CDF 在 0 处）
    p, _, _ = ml_model.predict_interval(16000, 16000, years=3, plan=40, rank_cv=0.1)
    assert abs(p - 0.5) < 1e-6


def test_prob_monotonic_in_student_rank():
    # 位次越靠前（数字越小）概率越高
    better = ml_model.predict_prob(8000, 16000, 0.3)
    worse = ml_model.predict_prob(30000, 16000, 0.3)
    assert better > 0.5 > worse
