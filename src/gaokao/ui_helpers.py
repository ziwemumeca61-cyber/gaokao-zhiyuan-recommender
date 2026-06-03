"""Streamlit 各页面共用的 UI 辅助函数：会话状态、心愿单、专业科普卡、雷达图等。"""

from __future__ import annotations

import streamlit as st

from .data_loader import data_available, load_majors, load_schools
from .models import RIASEC_DIMENSIONS, RIASEC_LABELS, Major, Student


def ensure_data() -> bool:
    """确保模拟数据存在；缺失时尝试自动生成。返回是否可用。"""
    if data_available():
        return True
    try:
        import sys
        from pathlib import Path

        data_dir = Path(__file__).resolve().parents[2] / "data"
        sys.path.insert(0, str(data_dir))
        import generate_mock_data  # noqa: PLC0415

        generate_mock_data.main()
        return data_available()
    except Exception as e:  # noqa: BLE001
        st.error(f"数据不可用且自动生成失败：{e}\n请运行 `python data/generate_mock_data.py`")
        return False


# ---------- 会话状态 ----------
def get_student() -> Student | None:
    return st.session_state.get("student")


def set_student(student: Student) -> None:
    st.session_state["student"] = student


def require_student() -> Student | None:
    student = get_student()
    if student is None:
        st.warning("请先到 **📝 信息录入** 页填写你的分数与位次。")
        st.page_link("pages/1_📝_信息录入.py", label="➡️ 去填写信息", icon="📝")
        return None
    return student


# ---------- 心愿单 ----------
def get_wishlist() -> list[str]:
    return st.session_state.setdefault("wishlist", [])


def in_wishlist(major_id: str) -> bool:
    return major_id in get_wishlist()


def toggle_wishlist(major_id: str) -> None:
    wl = get_wishlist()
    if major_id in wl:
        wl.remove(major_id)
    else:
        wl.append(major_id)


# ---------- 渲染组件 ----------
def render_major_detail(major: Major) -> None:
    """专业科普详情：是什么 / 学什么 / 干什么 / 适合谁。"""
    if major.intro:
        st.markdown(f"**这是什么** ｜ {major.intro}")
    if major.core_courses:
        st.markdown("**主修课程** ｜ " + "、".join(major.core_courses))
    if major.career_paths:
        st.markdown("**就业方向** ｜ " + "、".join(major.career_paths))
    if major.industry_outlook:
        st.markdown(f"**行业前景** ｜ {major.industry_outlook}")
    if major.suits:
        st.markdown(f"**适合谁** ｜ {major.suits}")
    st.caption(f"学科门类：{major.category}　就业率：{major.employment_rate * 100:.0f}%"
               f"　热度：{major.heat:.0f}")


def wishlist_button(major: Major, key: str) -> None:
    label = "💔 移出心愿单" if in_wishlist(major.id) else "❤️ 加入心愿单"
    if st.button(label, key=key):
        toggle_wishlist(major.id)
        st.rerun()


def riasec_radar(riasec: dict[str, float], title: str = "兴趣画像"):
    """返回 RIASEC 雷达图（plotly Figure）。"""
    import plotly.graph_objects as go  # noqa: PLC0415

    labels = [f"{d} {RIASEC_LABELS[d]}" for d in RIASEC_DIMENSIONS]
    values = [riasec.get(d, 0.0) for d in RIASEC_DIMENSIONS]
    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]], theta=labels + [labels[0]],
        fill="toself", line_color="#FF5A5F"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False, title=title, height=380)
    return fig


def school_caption(school) -> str:
    badge = "·".join([school.level, school.type])
    return f"{school.name}（{school.city} · {badge}）"


def major_by_name(name: str) -> Major | None:
    for m in load_majors().values():
        if m.name == name:
            return m
    return None


def school_of(major: Major):
    return load_schools().get(major.school_id)
