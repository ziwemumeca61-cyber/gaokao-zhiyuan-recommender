"""一分一段换算测试。"""

from gaokao import rank_score


def _table():
    return rank_score.build_table("四川", "物理")


def test_build_table_ok():
    t = _table()
    assert t is not None
    assert t.score_min < t.score_max
    assert t.rank_best < t.rank_worst


def test_insufficient_data_returns_none():
    # 数据生成器里没有"西藏" -> 数据不足
    assert rank_score.build_table("西藏", "物理") is None


def test_higher_score_means_smaller_rank():
    t = _table()
    lo = t.rank_for_score(t.score_min + 5).value
    hi = t.rank_for_score(t.score_max - 5).value
    assert hi <= lo  # 分数更高 -> 位次更小（更好）


def test_in_range_not_clamped_out_of_range_clamped():
    t = _table()
    mid = (t.score_min + t.score_max) // 2
    assert t.rank_for_score(mid).clamped is False
    assert t.rank_for_score(t.score_max + 50).clamped is True
    assert t.rank_for_score(t.score_min - 50).clamped is True


def test_roundtrip_score_rank_score_within_range():
    t = _table()
    for sc in (t.score_min + 3, (t.score_min + t.score_max) // 2, t.score_max - 3):
        r = t.rank_for_score(sc).value
        back = t.score_for_rank(r).value
        assert abs(back - sc) <= 2  # 往返误差很小


def test_extrapolation_monotonic_beyond_range():
    """范围外外推仍单调：更高的分对应更小的位次。"""
    t = _table()
    r1 = t.rank_for_score(t.score_max + 10).value
    r2 = t.rank_for_score(t.score_max + 40).value
    assert r2 < r1


def test_score_for_rank_out_of_range_clamped():
    t = _table()
    assert t.score_for_rank(t.rank_best // 2).clamped is True
    assert t.score_for_rank(t.rank_worst * 2).clamped is True
