"""控制线数据与定位文案测试。"""
from gaokao import control_lines as cl


def test_lookup_known_provinces():
    for prov, subj in [("山东", "综合"), ("河南", "物理"), ("广东", "历史")]:
        c = cl.lookup(prov, subj)
        assert c is not None and c.year == 2026
        assert 200 < c.benke < c.tekong < 750  # 本科线 < 特控线，且合理范围


def test_describe_over_and_under_line():
    over = cl.describe("山东", "综合", 600)
    assert over and "超本科线" in over
    under = cl.describe("四川", "历史", 400)  # 四川历史本科线455
    assert under and "未达本科线" in under


def test_coverage_at_least_28_provinces():
    assert len(cl.available_provinces()) >= 28
