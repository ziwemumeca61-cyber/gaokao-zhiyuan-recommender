from gaokao.recommender import interest


def test_neutral_when_no_assessment():
    riasec = {d: 0.0 for d in "RIASEC"}
    assert interest.match(riasec, "IR") == 0.5


def test_high_match_for_aligned_interest():
    riasec = {"R": 0.2, "I": 0.9, "A": 0.1, "S": 0.1, "E": 0.1, "C": 0.2}
    high = interest.match(riasec, "I")
    low = interest.match(riasec, "S")
    assert high > low
    assert high > 0.7


def test_code_to_vector_weights_first_dim_highest():
    vec = interest.code_to_vector("IR")
    # I 维权重应高于 R 维
    assert vec[1] > vec[0]
