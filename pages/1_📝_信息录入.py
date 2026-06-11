"""信息录入：填写分数、位次与偏好，生成考生画像。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import (  # noqa: E402
    available_categories, available_cities, available_provinces, available_subjects,
)
from gaokao.electives import ELECTIVE_SUBJECTS  # noqa: E402
from gaokao.models import Student  # noqa: E402
from gaokao.ui_helpers import ensure_data, get_student  # noqa: E402

st.title("📝 信息录入")
st.caption("填写你的高考信息与偏好，系统据此为你量身推荐。带 * 为必填。")

if not ensure_data():
    st.stop()

existing = get_student()
provinces = available_provinces()
cities = available_cities()
categories = available_categories()

# 省份放在表单外：切换省份即刷新可选科类（不同省份科类不同，如 3+3 省份为"综合"）
province = st.selectbox(
    "生源所在省份 *", provinces,
    index=provinces.index(existing.province) if existing
    and existing.province in provinces else 0,
    help="即你高考报名的省份。高考按省份分别划线录取，"
         "所有分数线/位次都基于此省，跨省不可直接比较。")
subjects = available_subjects(province) or ["物理", "历史"]
# 科类放表单外：切换即刷新（综合=3+3 才需要填选考科目）
subject_type = st.radio(
    "选科科类 *", subjects,
    index=subjects.index(existing.subject_type) if (
        existing and existing.subject_type in subjects) else 0,
    horizontal=True)

electives: list[str] = existing.electives if existing else []
if subject_type == "综合":
    electives = st.multiselect(
        "选考科目 *（3+3 省份请选 3 门，用于过滤你不能报的专业）",
        list(ELECTIVE_SUBJECTS), default=[e for e in electives if e in ELECTIVE_SUBJECTS],
        max_selections=3)
    if len(electives) != 3:
        st.caption("⚠️ 请选满 3 门；不选则不按选科要求过滤，可能推到你报不了的专业。")

with st.form("student_form"):
    c1, c2 = st.columns(2)
    with c1:
        score = st.number_input("高考分数 *", min_value=200, max_value=900,
                                value=int(existing.score) if existing else 600)
    with c2:
        rank = st.number_input("全省位次 *", min_value=1, max_value=900000,
                               value=int(existing.rank) if existing else 15000,
                               help="位次比分数更稳定，是志愿推荐的核心依据")

    st.markdown("**偏好（可选，用于个性化排序）**")
    c3, c4, c5 = st.columns(3)
    with c3:
        level_pref = st.selectbox(
            "院校层次偏好", ["不限", "985", "211", "双一流", "普通"],
            index=0)
    with c4:
        city_prefs = st.multiselect("意向城市", cities,
                                    default=existing.city_prefs if existing else [])
    with c5:
        major_prefs = st.multiselect("意向专业门类", categories,
                                     default=existing.major_prefs if existing else [])

    st.markdown("**家庭与发展意向（可选，让避坑提示更懂你）**")
    f1, f2, f3 = st.columns(3)
    _econ_opts = ["不便透露", "一般", "宽裕"]
    with f1:
        family_economy = st.selectbox(
            "家庭经济", _econ_opts,
            index=_econ_opts.index(existing.family_economy) if (
                existing and existing.family_economy in _econ_opts) else 0)
    with f2:
        accept_postgrad = st.radio(
            "是否接受读研深造", ["接受", "暂不打算"],
            index=0 if (not existing or existing.accept_postgrad) else 1,
            horizontal=True)
    with f3:
        _intent_opts = ["还没想好", "考公考编", "进企业"]
        career_intent = st.selectbox(
            "毕业去向倾向", _intent_opts,
            index=_intent_opts.index(existing.career_intent) if (
                existing and existing.career_intent in _intent_opts) else 0)

    submitted = st.form_submit_button("💾 保存并生成画像", type="primary")

st.page_link("pages/10_🔢_一分一段.py",
             label="🔢 不确定分数对应的位次？用一分一段表换算", icon="🔢")

if submitted:
    student = Student(
        score=float(score), rank=int(rank), province=province,
        subject_type=subject_type, electives=list(electives),
        city_prefs=city_prefs, major_prefs=major_prefs,
        level_pref=None if level_pref == "不限" else level_pref,
        family_economy="" if family_economy == "不便透露" else family_economy,
        accept_postgrad=(accept_postgrad == "接受"),
        career_intent="" if career_intent == "还没想好" else career_intent,
    )
    # 保留既有兴趣测评结果
    if existing and existing.has_assessment():
        student.riasec = dict(existing.riasec)
    from gaokao.ui_helpers import set_student

    set_student(student)
    st.success("✅ 已保存！现在可以去 **🎯 志愿推荐** 或 **🧭 兴趣测评** 了。")
    st.page_link("pages/3_🎯_志愿推荐.py", label="➡️ 直接看志愿推荐", icon="🎯")
    st.page_link("pages/2_🧭_兴趣测评.py", label="➡️ 先做兴趣测评（更懂你）", icon="🧭")

if existing:
    st.divider()
    st.caption(f"当前画像：{existing.province} · {existing.subject_type} · "
               f"分数 {existing.score} · 位次 {existing.rank}"
               + ("（已完成兴趣测评）" if existing.has_assessment() else ""))
