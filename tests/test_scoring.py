from gaokao.models import Major, School, Student
from gaokao.recommender import scoring


def _student(**kw):
    base = dict(score=600, rank=10000, province="四川", subject_type="物理")
    base.update(kw)
    return Student(**base)


def _school(level="985", city="成都"):
    return School(id="S1", name="某大学", province="四川", city=city,
                  level=level, type="综合")


def _major(category="工学", heat=90.0, employ=0.95):
    return Major(id="M1", name="计算机", category=category, school_id="S1",
                 riasec_code="IR", heat=heat, employment_rate=employ)


def test_composite_in_unit_range():
    s = scoring.composite(_student(), _school(), _major(), 0.8, 0.7)
    assert 0.0 <= s <= 1.0


def test_higher_probability_raises_score():
    low = scoring.composite(_student(), _school(), _major(), 0.2, 0.5)
    high = scoring.composite(_student(), _school(), _major(), 0.9, 0.5)
    assert high > low


def test_city_preference_boosts_score():
    pref = _student(city_prefs=["成都"])
    nopref = _student(city_prefs=["北京"])
    assert (scoring.composite(pref, _school(city="成都"), _major(), 0.5, 0.5)
            > scoring.composite(nopref, _school(city="成都"), _major(), 0.5, 0.5))
