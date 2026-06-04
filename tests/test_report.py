"""导出报告测试：Markdown 必测；Word/PDF 依赖缺失时优雅跳过对应断言。"""

from gaokao import report
from gaokao.models import Major, School, Student
from gaokao.recommender import engine


def _student():
    return Student(score=620, rank=15000, province="四川", subject_type="物理",
                   level_pref="985", city_prefs=["成都"])


def _wishlist_items():
    school = School(id="S1", name="测试大学", province="四川", city="成都",
                    level="985", type="综合")
    major = Major(id="M1", name="计算机科学与技术", category="工学", school_id="S1",
                  riasec_code="IR", heat=95.0, employment_rate=0.93,
                  intro="研究计算系统与软件的学科。")
    return [(school, major)]


# ---------- Markdown（零依赖，必测） ----------
def test_markdown_report_has_sections():
    buckets = engine.recommend(_student(), per_tier=5)
    md = report.build_markdown_report(_student(), buckets)
    assert "# 高考志愿推荐报告" in md
    assert "考生画像" in md and "志愿推荐明细" in md
    for tier in ("冲", "稳", "保"):
        assert f"### {tier}" in md


def test_markdown_wishlist_lists_items_in_order():
    md = report.build_markdown_wishlist(_student(), _wishlist_items())
    assert "# 我的志愿表" in md
    assert "测试大学" in md and "计算机科学与技术" in md
    assert "1. 测试大学" in md


def test_markdown_wishlist_handles_empty():
    md = report.build_markdown_wishlist(_student(), [])
    assert "共 0 个" in md
    assert "心愿单为空" in md


# ---------- PDF（reportlab 可用时才测，契合优雅降级） ----------
def test_pdf_available_returns_bool():
    assert isinstance(report.pdf_available(), bool)


def test_pdf_report_bytes_when_available():
    if not report.pdf_available():
        return
    buckets = engine.recommend(_student(), per_tier=3)
    data = report.build_pdf_report(_student(), buckets)
    assert isinstance(data, bytes) and data.startswith(b"%PDF")


def test_pdf_wishlist_bytes_when_available():
    if not report.pdf_available():
        return
    data = report.build_pdf_wishlist(_student(), _wishlist_items())
    assert isinstance(data, bytes) and data.startswith(b"%PDF")


# ---------- Word（python-docx 可用时才测） ----------
def test_docx_available_returns_bool():
    assert isinstance(report.docx_available(), bool)


def test_docx_wishlist_bytes_when_available():
    if not report.docx_available():
        return
    data = report.build_docx_wishlist(_student(), _wishlist_items())
    # docx 即 zip 容器，魔数 PK
    assert isinstance(data, bytes) and data.startswith(b"PK")
