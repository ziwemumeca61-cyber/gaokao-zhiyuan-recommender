from gaokao.recommender import rank_based as rb


def test_stable_when_rank_close():
    # 考生位次与院校位次相近 -> 稳
    assert rb.classify(10000, 10000) == "稳"


def test_rush_when_student_rank_worse():
    # 考生位次更靠后（数字更大）-> 冲
    assert rb.classify(12000, 10000) == "冲"


def test_safe_when_student_rank_better():
    # 考生位次明显更靠前（数字更小）-> 保
    assert rb.classify(7000, 10000) == "保"


def test_out_of_range_returns_none():
    assert rb.classify(50000, 10000) is None   # 太冒险
    assert rb.classify(1000, 10000) is None     # 太浪费


def test_ratio_safe_against_zero_ref():
    assert rb.ratio(10000, 0) == 1.0
