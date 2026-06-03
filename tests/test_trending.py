from gaokao.models import Major
from gaokao.recommender import trending


def _majors():
    return {
        "M1": Major(id="M1", name="计算机科学与技术", category="工学", school_id="S1",
                    riasec_code="IR", heat=98, employment_rate=0.95),
        "M2": Major(id="M2", name="计算机科学与技术", category="工学", school_id="S2",
                    riasec_code="IR", heat=96, employment_rate=0.94),
        "M3": Major(id="M3", name="生物科学", category="理学", school_id="S1",
                    riasec_code="IR", heat=45, employment_rate=0.72),
    }


def test_hot_ranking_orders_by_score():
    trends = trending.rank_hot_majors(_majors())
    assert trends[0].name == "计算机科学与技术"
    assert trends[0].score > trends[-1].score


def test_breadth_counts_schools():
    trends = trending.rank_hot_majors(_majors())
    cs = next(t for t in trends if t.name == "计算机科学与技术")
    assert cs.count == 2


def test_category_filter():
    trends = trending.rank_hot_majors(_majors(), category="理学")
    assert all(t.category == "理学" for t in trends)


def test_hot_major_names_returns_set():
    names = trending.hot_major_names(_majors(), top_n=1)
    assert names == {"计算机科学与技术"}
