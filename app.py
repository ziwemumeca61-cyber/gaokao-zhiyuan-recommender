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

from gaokao import branding  # noqa: E402

st.set_page_config(page_title=branding.get("app_title"),
                   page_icon=branding.get("app_icon"), layout="wide")


def _inject_responsive_css() -> None:
    """注入手机端友好样式：窄屏下多列自动堆叠、留白收紧、字号与点按区域加大。

    通过 st.navigation 时本入口每次都会执行，故在此注入即可覆盖所有页面。
    """
    st.markdown(
        """
        <style>
        /* 收紧顶部/两侧留白，手机上更省空间 */
        .block-container { padding-top: 2.2rem; padding-bottom: 3rem; }
        @media (max-width: 640px) {
            .block-container { padding-left: .8rem !important;
                               padding-right: .8rem !important; padding-top: 1.2rem; }
            /* 关键：窄屏下让 st.columns 自动竖排，冲/稳/保等三列不再被挤成窄条 */
            div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .4rem; }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
            }
            /* 正文与标题在手机上更易读 */
            html, body, [class*="css"] { font-size: 16px; }
            h1 { font-size: 1.6rem !important; }
            h2 { font-size: 1.35rem !important; }
            h3 { font-size: 1.15rem !important; }
            /* 按钮/下载键点按区域加大、整行更好点 */
            .stButton > button, .stDownloadButton > button {
                min-height: 2.9rem; width: 100%; font-size: 1rem;
            }
            /* 表单控件放大，手指更好操作 */
            div[data-baseweb="select"], .stNumberInput input, .stTextInput input {
                min-height: 2.7rem; font-size: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_responsive_css()


def render_home() -> None:
    """引导式首页：数据徽章 + 三步走 + 动态下一步。"""
    from gaokao.data_loader import (  # noqa: PLC0415
        active_source, admission_count, available_provinces, load_majors, load_schools,
    )
    from gaokao.ui_helpers import ensure_data, get_student  # noqa: PLC0415

    st.title(f"{branding.get('app_icon')} {branding.get('app_title')}")
    st.subheader(branding.get("subtitle"))
    if branding.get("org_name"):
        st.caption(f"由 {branding.get('org_name')} 提供")

    if not ensure_data():
        st.stop()

    _, is_real = active_source()
    if is_real:
        st.success(
            f"✅ **真实数据** · 已覆盖 {len(available_provinces())} 省 · "
            f"{len(load_schools())} 所院校 · {len(load_majors())} 个专业 · "
            f"{admission_count():,} 条录取记录")
    else:
        st.info("🧪 当前为**演示数据**（模拟），仅供体验；导入真实数据后自动切换"
                "（见 ⚙️ 数据源）。")

    student = get_student()
    st.divider()

    if not student:
        # 首页即填：手机上一进来就填这三项，直接出推荐（无需先跳页）
        from gaokao import rank_score  # noqa: PLC0415
        from gaokao.data_loader import available_subjects  # noqa: PLC0415
        from gaokao.models import Student  # noqa: PLC0415
        from gaokao.ui_helpers import set_student  # noqa: PLC0415

        st.markdown("#### 🚀 一分钟开始：填好这三项，直接看推荐")
        provinces = available_provinces()
        qp = st.selectbox("你的省份", provinces, key="home_prov",
                          help="高考按省份分别划线录取，分数线/位次都基于此省。")
        subs = available_subjects(qp) or ["物理", "历史"]
        # 不设 key，切换省份时科类自动回到首项，避免出现该省没有的旧科类
        qs = st.radio("选科科类", subs, horizontal=True)
        qscore = st.number_input("高考分数", min_value=200, max_value=900,
                                 value=550, key="home_score")

        table = rank_score.build_table(qp, qs)
        est_rank = None
        if table is not None:
            conv = table.rank_for_score(int(qscore))
            est_rank = conv.value
            st.caption(f"约第 **{est_rank:,}** 名（{qp}一分一段换算，位次是推荐核心依据）")
        else:
            st.caption("该省暂无一分一段换算表，可到『信息录入』手动填位次。")

        if st.button("🎯 开始：看我的冲稳保推荐", type="primary",
                     use_container_width=True):
            set_student(Student(
                score=float(qscore), rank=int(est_rank or 50000),
                province=qp, subject_type=qs, electives=[]))
            st.switch_page(recommend_page)

        if qs == "综合":
            st.caption("💡 3+3 省份建议到 **信息录入** 补选 3 门选考科目，"
                       "以过滤你不能报的专业。")
        st.caption("想填城市/专业偏好、做兴趣测评让推荐更懂你？")
        h1, h2 = st.columns(2)
        with h1:
            st.page_link(info_page, label="填更多偏好（可选）", icon="📝")
        with h2:
            if st.button("🎲 先用示例考生体验", use_container_width=True):
                sub0 = subs[0]
                set_student(Student(
                    score=573, rank=50000, province=qp, subject_type=sub0,
                    electives=["物理", "化学", "生物"] if sub0 == "综合" else []))
                st.switch_page(recommend_page)
    elif not st.session_state.get("recommendations"):
        if st.button(f"🎯 下一步：看 {student.province}·{student.subject_type}·{student.score}分 的冲稳保推荐",
                     type="primary", use_container_width=True):
            st.switch_page(recommend_page)
    else:
        if st.button("❤️ 下一步：整理 / 导出我的志愿表",
                     type="primary", use_container_width=True):
            st.switch_page(wishlist_page)

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

    st.caption("⚠️ " + branding.get("disclaimer"))


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
school_page = st.Page("pages/12_🏛️_院校查询.py", title="院校查询", icon="🏛️")
datasource_page = st.Page("pages/11_⚙️_数据源.py", title="数据源", icon="⚙️")

nav = st.navigation({
    "🏠 开始": [home_page, info_page],
    "🎯 推荐与选校": [recommend_page, cards_page, wishlist_page, dashboard_page,
                compare_page],
    "🧰 查询工具": [assess_page, rankscore_page, school_page, encyclo_page, ai_page],
    "⚙️ 设置": [datasource_page],
})
nav.run()
