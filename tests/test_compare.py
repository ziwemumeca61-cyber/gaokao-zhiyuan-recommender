"""院校对比模块测试。"""

from gaokao.data_loader import load_admissions
from gaokao.models import Student
from gaokao.recommender import compare
from gaokao.recommender.history import aggregate


def _student():
    return Student(score=620, rank=15000, province="四川", subject_type="物理")


def _some_pairs(n=3):
    """从四川物理有数据的记录里取前 n 个 (school_id, major_id)。"""
    stats = aggregate(load_admissions(), "四川", "物理")
    return list(stats.keys())[:n]


def test_compare_preserves_input_order_and_count():
    pairs = _some_pairs(3)
    rows = compare.compare(_student(), pairs)
    assert len(rows) == 3
    assert [(r.school.id, r.major.id) for r in rows] == pairs


def test_compare_rows_have_valid_metrics():
    rows = compare.compare(_student(), _some_pairs(4))
    for r in rows:
        assert r.has_data
        assert 0.0 <= r.prob_low <= r.probability <= r.prob_high <= 1.0
        assert 0.0 <= r.composite_score <= 1.0
        assert r.tier in ("冲", "稳", "保", "")
        assert r.ref_rank > 0


def test_compare_skips_unknown_ids():
    pairs = _some_pairs(2) + [("NOPE", "NOPE")]
    rows = compare.compare(_student(), pairs)
    assert len(rows) == 2  # 无效 id 被跳过


def test_compare_marks_missing_province_data():
    """构造一个该省无数据的 (校,专业)：取存在的 id 但换一个没有记录的省份。"""
    pairs = _some_pairs(1)
    # 用一个数据生成器里不存在的省份，使聚合查不到 -> has_data=False
    student = Student(score=600, rank=10000, province="西藏", subject_type="物理")
    rows = compare.compare(student, pairs)
    assert len(rows) == 1
    assert rows[0].has_data is False
    assert rows[0].ref_rank == 0


def test_best_index_picks_highest_composite():
    rows = compare.compare(_student(), _some_pairs(4))
    idx = compare.best_index(rows)
    assert idx is not None
    best = max(r.composite_score for r in rows if r.has_data)
    assert rows[idx].composite_score == best


def test_best_index_none_when_no_data():
    student = Student(score=600, rank=10000, province="西藏", subject_type="物理")
    rows = compare.compare(student, _some_pairs(2))
    assert compare.best_index(rows) is None
