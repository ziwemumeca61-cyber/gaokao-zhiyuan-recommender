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


# ---------- 省份口径（高考按省录取，跨省分数线不可比） ----------
def scope_label(student: Student) -> str:
    """考生的生源省份+科类口径，用于在各处标注分数线/位次的适用范围。"""
    return f"{student.province}·{student.subject_type}"


def render_scope_banner(student: Student) -> None:
    """在展示分数线/位次的页面顶部标注省份口径，提醒跨省不可直接比较。"""
    st.info(
        f"📍 以下分数线/位次均按 **{student.province} · {student.subject_type}** 口径测算。"
        "高考按省份分别划线录取，不同省份的分数/位次不可直接比较。")


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


def remove_from_wishlist(major_id: str) -> None:
    wl = get_wishlist()
    if major_id in wl:
        wl.remove(major_id)


def move_wishlist_item(major_id: str, delta: int) -> None:
    """在心愿单内把某专业上移(delta<0)或下移(delta>0)；越界自动夹紧。"""
    wl = get_wishlist()
    if major_id not in wl:
        return
    i = wl.index(major_id)
    j = max(0, min(len(wl) - 1, i + delta))
    if i != j:
        wl.insert(j, wl.pop(i))


def wishlist_items() -> list[tuple[object, Major]]:
    """按心愿单顺序返回 (School|None, Major) 列表，跳过已失效的专业 id。"""
    majors = load_majors()
    schools = load_schools()
    items: list[tuple[object, Major]] = []
    for mid in get_wishlist():
        m = majors.get(mid)
        if m is not None:
            items.append((schools.get(m.school_id), m))
    return items


# ---------- 渲染组件 ----------
def render_major_detail(major: Major) -> None:
    """专业科普详情：是什么 / 学什么 / 干什么 / 适合谁（缺失字段用知识库兜底）。"""
    from .major_knowledge import detail_for  # noqa: PLC0415

    d = detail_for(major)
    st.markdown(f"**专业简介** ｜ {d['intro']}")
    st.markdown("**主修课程** ｜ " + "、".join(d["core_courses"]))
    st.markdown("**就业去向** ｜ " + "、".join(d["career_paths"]))
    if d["industry_outlook"]:
        st.markdown(f"**行业前景** ｜ {d['industry_outlook']}")
    if d["suits"]:
        st.markdown(f"**适合谁** ｜ {d['suits']}")
    if major.subject_req:
        from .electives import requirement_label  # noqa: PLC0415

        st.markdown(f"**选科要求** ｜ {requirement_label(major.subject_req)}")

    # 中肯的选报建议 + 结合家庭情况的提醒
    from .major_advice import advice_for, family_notes  # noqa: PLC0415

    adv = advice_for(major.name, major.category)
    st.markdown(f"**⚠️ 选专业提示** ｜ {adv['pitfall']}")
    st.markdown(f"**💬 实在话** ｜ {adv['truth']}")
    st.markdown(f"**👪 适合谁** ｜ {adv['fit']}")
    stu = get_student()
    if stu is not None:
        for note in family_notes(major.name, major.category,
                                 family_economy=stu.family_economy,
                                 accept_postgrad=stu.accept_postgrad,
                                 career_intent=stu.career_intent):
            st.markdown(f"**🎯 给你的提醒** ｜ {note}")
    st.caption(f"学科门类：{major.category}　|　以上为行业普遍看法，仅供参考")


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
        fill="toself", line_color="#1FA463"))
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
