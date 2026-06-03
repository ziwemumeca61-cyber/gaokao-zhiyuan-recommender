from gaokao.models import TIERS, Student
from gaokao.recommender import engine
from gaokao.report import build_markdown_report


def _student():
    return Student(score=620, rank=15000, province="四川", subject_type="物理",
                   level_pref="985", city_prefs=["成都"])


def test_engine_returns_all_tiers():
    buckets = engine.recommend(_student(), per_tier=5)
    assert set(buckets.keys()) == set(TIERS)


def test_engine_respects_per_tier_limit():
    buckets = engine.recommend(_student(), per_tier=3)
    for tier in TIERS:
        assert len(buckets[tier]) <= 3


def test_engine_sorted_by_composite():
    buckets = engine.recommend(_student(), per_tier=10)
    for tier in TIERS:
        scores = [r.composite_score for r in buckets[tier]]
        assert scores == sorted(scores, reverse=True)


def test_engine_produces_some_recommendations():
    buckets = engine.recommend(_student(), per_tier=10)
    total = sum(len(buckets[t]) for t in TIERS)
    assert total > 0


def test_recommendations_have_reasons():
    buckets = engine.recommend(_student(), per_tier=5)
    for tier in TIERS:
        for rec in buckets[tier]:
            assert rec.reasons
            assert rec.tier == tier


def test_markdown_report_contains_key_sections():
    student = _student()
    buckets = engine.recommend(student, per_tier=5)
    md = build_markdown_report(student, buckets)
    assert "高考志愿推荐报告" in md
    assert "考生画像" in md
    assert str(student.rank) in md
    for tier in TIERS:
        assert tier in md
