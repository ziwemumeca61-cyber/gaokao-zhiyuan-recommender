"""信息录入：填写分数、位次与偏好，生成考生画像。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import (  # noqa: E402
    available_categories, available_cities, available_provinces,
)
from gaokao.models import Student  # noqa: E402
from gaokao.ui_helpers import ensure_data, get_student  # noqa: E402

st.set_page_config(page_title="信息录入", page_icon="📝", layout="wide")
st.title("📝 信息录入")
st.caption("填写你的高考信息与偏好，系统据此为你量身推荐。带 * 为必填。")

if not ensure_data():
    st.stop()

existing = get_student()
provinces = available_provinces()
cities = available_cities()
categories = available_categories()

with st.form("student_form"):
    c1, c2 = st.columns(2)
    with c1:
        score = st.number_input("高考分数 *", min_value=200, max_value=750,
                                value=int(existing.score) if existing else 600)
        province = st.selectbox(
            "考试省份 *", provinces,
            index=provinces.index(existing.province) if existing
            and existing.province in provinces else 0)
    with c2:
        rank = st.number_input("全省位次 *", min_value=1, max_value=500000,
                               value=int(existing.rank) if existing else 15000,
                               help="位次比分数更稳定，是志愿推荐的核心依据")
        subject_type = st.radio(
            "选科科类 *", ["物理", "历史"],
            index=0 if not existing or existing.subject_type == "物理" else 1,
            horizontal=True)

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

    submitted = st.form_submit_button("💾 保存并生成画像", type="primary")

if submitted:
    student = Student(
        score=float(score), rank=int(rank), province=province,
        subject_type=subject_type,
        city_prefs=city_prefs, major_prefs=major_prefs,
        level_pref=None if level_pref == "不限" else level_pref,
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
