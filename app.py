"""高考志愿填报推荐系统 — Streamlit 入口。

用 st.navigation 把多页分组，并提供"三步走"引导式首页。
运行：  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 兼容未做 editable 安装的环境
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="高考志愿小助手", page_icon="🎓", layout="wide")


def render_home() -> None:
    """引导式首页：数据徽章 + 三步走 + 动态下一步。"""
    from gaokao.data_loader import (  # noqa: PLC0415
        active_source, available_provinces, load_admissions, load_majors, load_schools,
    )
    from gaokao.ui_helpers import ensure_data, get_student  # noqa: PLC0415

    st.title("🎓 高考志愿小助手")
    st.subheader("分数不浪费，专业不踩坑，志愿填得明明白白 ✨")

    if not ensure_data():
        st.stop()

    _, is_real = active_source()
    if is_real:
        st.success(
            f"✅ 当前为**真实数据**（{'、'.join(available_provinces())}）："
            f"{len(load_schools())} 所院校 · {len(load_majors())} 个专业 · "
            f"{len(load_admissions()):,} 条录取记录")
    else:
        st.info("🧪 当前为**演示数据**（模拟），仅供体验；导入真实数据后自动切换"
                "（见 ⚙️ 数据源）。")

    student = get_student()

    st.divider()
    st.markdown("### 跟着三步走，志愿表轻松搞定")
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown("#### 1️⃣ 填写信息")
        st.caption("分数 · 位次 · 省份 · 偏好")
        st.markdown("✅ 已完成" if student else "⬜ 待完成")
        st.page_link(info_page, label="去填写 / 修改", icon="📝")
    with c2, st.container(border=True):
        st.markdown("#### 2️⃣ 看冲稳保推荐")
        st.caption("基于真实录取线的志愿表")
        st.markdown("✅ 可查看" if student else "⬜ 需先完成第 1 步")
        st.page_link(recommend_page, label="查看推荐", icon="🎯")
    with c3, st.container(border=True):
        st.markdown("#### 3️⃣ 选校 · 对比 · 导出")
        st.caption("心愿单排序 · 院校对比 · 一键导出")
        st.markdown("✅ 可整理" if st.session_state.get("wishlist") else "⬜ 先把心仪专业加入心愿单")
        st.page_link(wishlist_page, label="我的志愿表", icon="❤️")

    st.divider()
    if not student:
        st.markdown("#### 👉 现在开始")
        st.page_link(info_page, label="第一步：填写我的高考信息", icon="📝")
    elif not st.session_state.get("recommendations"):
        st.markdown(f"#### 👋 {student.province}·{student.subject_type} · {student.score} 分 考生，欢迎回来")
        st.page_link(recommend_page, label="下一步：查看我的冲稳保推荐", icon="🎯")
    else:
        st.markdown("#### 🎉 推荐已生成，去整理你的志愿表吧")
        st.page_link(wishlist_page, label="下一步：整理 / 导出我的志愿表", icon="❤️")

    st.divider()
    st.markdown("##### 🧰 辅助工具")
    t = st.columns(4)
    with t[0]:
        st.page_link(assess_page, label="兴趣测评", icon="🧭")
    with t[1]:
        st.page_link(rankscore_page, label="分数↔位次", icon="🔢")
    with t[2]:
        st.page_link(encyclo_page, label="专业百科", icon="📚")
    with t[3]:
        st.page_link(dashboard_page, label="志愿体检", icon="📋")

    st.caption("⚠️ 结果仅供参考，正式填报请以各省考试院与院校招生章程为准。")


# ---- 页面注册（供导航与首页按钮引用） ----
home_page = st.Page(render_home, title="首页", icon="🏠", default=True)
info_page = st.Page("pages/1_📝_信息录入.py", title="信息录入", icon="📝")
assess_page = st.Page("pages/2_🧭_兴趣测评.py", title="兴趣测评", icon="🧭")
recommend_page = st.Page("pages/3_🎯_志愿推荐.py", title="志愿推荐", icon="🎯")
cards_page = st.Page("pages/4_🃏_卡片选校.py", title="卡片选校", icon="🃏")
encyclo_page = st.Page("pages/5_📚_专业百科.py", title="专业百科", icon="📚")
dashboard_page = st.Page("pages/6_📊_数据大屏.py", title="志愿体检", icon="📋")
ai_page = st.Page("pages/7_🤖_AI助手.py", title="AI 助手", icon="🤖")
wishlist_page = st.Page("pages/8_❤️_我的志愿表.py", title="我的志愿表", icon="❤️")
compare_page = st.Page("pages/9_🆚_院校对比.py", title="院校对比", icon="🆚")
rankscore_page = st.Page("pages/10_🔢_一分一段.py", title="一分一段换算", icon="🔢")
datasource_page = st.Page("pages/11_⚙️_数据源.py", title="数据源", icon="⚙️")

nav = st.navigation({
    "🏠 开始": [home_page, info_page],
    "🎯 推荐与选校": [recommend_page, cards_page, wishlist_page, compare_page],
    "🧰 查询工具": [assess_page, rankscore_page, encyclo_page, dashboard_page, ai_page],
    "⚙️ 设置": [datasource_page],
})
nav.run()
