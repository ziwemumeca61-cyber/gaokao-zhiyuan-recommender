"""选科要求解析与匹配测试。"""

from gaokao import electives as el


def test_parse_none():
    assert el.parse_requirement("不限") == ("none", [])
    assert el.parse_requirement("") == ("none", [])
    assert el.parse_requirement(None) == ("none", [])


def test_parse_single_required():
    assert el.parse_requirement("物理必选") == ("all", ["物理"])


def test_parse_all_required():
    assert el.parse_requirement("物理、化学(2科必选)") == ("all", ["物理", "化学"])
    assert el.parse_requirement("物化生(3科必选)") == ("all", ["物理", "化学", "生物"])


def test_parse_any_required():
    assert el.parse_requirement("物/化/生(3选1)") == ("any", ["物理", "化学", "生物"])
    assert el.parse_requirement("历史/地理(2选1)") == ("any", ["历史", "地理"])


def test_parse_zhengzhi_fullname():
    assert el.parse_requirement("思想政治必选") == ("all", ["政治"])


def test_satisfies_all():
    assert el.satisfies("物理、化学(2科必选)", ["物理", "化学", "生物"]) is True
    assert el.satisfies("物理、化学(2科必选)", ["物理", "生物", "地理"]) is False


def test_satisfies_any():
    assert el.satisfies("物/化/生(3选1)", ["生物", "政治", "地理"]) is True
    assert el.satisfies("物/化/生(3选1)", ["政治", "历史", "地理"]) is False


def test_satisfies_none_and_empty_electives():
    assert el.satisfies("不限", ["物理"]) is True
    # 未填选考科目时不过滤（视为满足）
    assert el.satisfies("物理必选", []) is True
