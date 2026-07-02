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
    """聚焦式首页：一个醒目的入口卡片为主角，数据/工具等次要信息收纳。"""
    from gaokao.data_loader import (  # noqa: PLC0415
        active_source, available_provinces, load_majors, load_schools,
    )
    from gaokao.ui_helpers import ensure_data, get_student  # noqa: PLC0415

    st.title(f"{branding.get('app_icon')} {branding.get('app_title')}")
    st.caption(branding.get("subtitle"))

    if not ensure_data():
        st.stop()

    # 数据可信度压成一行小字，不与主入口抢眼球
    _, is_real = active_source()
    if is_real:
        line = (f"✅ 真实数据 · 覆盖 {len(available_provinces())} 省 · "
                f"{len(load_schools())} 校 · {len(load_majors())} 专业")
        if branding.get("org_name"):
            line += f" · 由 {branding.get('org_name')} 提供"
        st.caption(line)
    else:
        st.caption("🧪 演示数据（模拟）；导入真实数据后自动切换（见 ⚙️ 数据源）。")

    student = get_student()

    if not student:
        _render_entry_card()
    elif not st.session_state.get("recommendations"):
        with st.container(border=True):
            st.markdown("### 👋 欢迎回来")
            st.write(f"已保存：**{student.province} · {student.subject_type} · "
                     f"{int(student.score)}分**（约第 {student.rank:,} 名）")
            if st.button("🎯 看我的冲稳保推荐", type="primary",
                         use_container_width=True):
                st.switch_page(recommend_page)
            st.page_link(info_page, label="修改我的信息", icon="📝")
    else:
        with st.container(border=True):
            st.markdown("### ✅ 推荐已生成")
            if st.button("❤️ 整理 / 导出我的志愿表", type="primary",
                         use_container_width=True):
                st.switch_page(wishlist_page)
            st.page_link(recommend_page, label="回看冲稳保推荐", icon="🎯")

    # 次要：更多工具收进折叠框，保持首页清爽
    with st.expander("🧰 更多工具：兴趣测评 · 一分一段 · 专业百科 · 院校查询 · 志愿体检"):
        tc = st.columns(2)
        with tc[0]:
            st.page_link(assess_page, label="兴趣测评", icon="🧭")
            st.page_link(encyclo_page, label="专业百科", icon="📚")
            st.page_link(dashboard_page, label="志愿体检", icon="📋")
        with tc[1]:
            st.page_link(rankscore_page, label="分数↔位次", icon="🔢")
            st.page_link(school_page, label="院校查询", icon="🏛️")

    st.caption("⚠️ " + branding.get("disclaimer"))


def _render_entry_card() -> None:
    """首页主角：醒目的一步式入口卡片——填三项直接出冲稳保。"""
    from gaokao import rank_score  # noqa: PLC0415
    from gaokao.data_loader import (  # noqa: PLC0415
        available_categories, available_cities, available_provinces, available_subjects,
    )
    from gaokao.models import Student  # noqa: PLC0415
    from gaokao.ui_helpers import set_student  # noqa: PLC0415

    with st.container(border=True):
        st.markdown("### 🚀 一分钟，出我的志愿表")
        st.caption("填下面三项，立刻看到你的冲 / 稳 / 保推荐")

        qp = st.selectbox("① 你的省份", available_provinces(), key="home_prov",
                          help="高考按省份分别划线录取，位次都基于此省。")
        subs = available_subjects(qp) or ["物理", "历史"]
        cc1, cc2 = st.columns(2)
        with cc1:
            # 不设 key：切换省份时科类回到首项，避免出现该省没有的旧科类
            qs = st.radio("② 选科科类", subs, horizontal=True)
        with cc2:
            qscore = st.number_input("③ 高考分数", min_value=200, max_value=900,
                                     value=550, key="home_score")

        table = rank_score.build_table(qp, qs)
        est_rank = None
        if table is not None:
            est_rank = table.rank_for_score(int(qscore)).value
            st.info(f"📊 你在 **{qp}** 约排 **第 {est_rank:,} 名**"
                    "　（位次是志愿推荐的核心依据）")
        else:
            st.caption("该省暂无一分一段换算表，可到『信息录入』手动填位次。")

        electives: list[str] = []
        with st.expander("🎛️ 更多偏好（可选：城市 / 专业 / 家庭 / 读研…）"):
            if qs == "综合":
                from gaokao.electives import ELECTIVE_SUBJECTS  # noqa: PLC0415
                electives = st.multiselect(
                    "选考科目（3+3 选 3 门，用于过滤你不能报的专业）",
                    list(ELECTIVE_SUBJECTS), max_selections=3, key="home_elect")
            level_pref = st.selectbox(
                "院校层次偏好", ["不限", "985", "211", "双一流", "普通"], key="home_level")
            city_prefs = st.multiselect("意向城市", available_cities(), key="home_city")
            major_prefs = st.multiselect(
                "意向专业门类", available_categories(), key="home_major")
            _econ = ["不便透露", "一般", "宽裕"]
            family_economy = st.selectbox("家庭经济", _econ, key="home_econ")
            accept_postgrad = st.radio(
                "是否接受读研深造", ["接受", "暂不打算"], horizontal=True, key="home_pg")
            _intent = ["还没想好", "考公考编", "进企业"]
            career_intent = st.selectbox("毕业去向倾向", _intent, key="home_career")

        if st.button("🎯 开始，看我的冲稳保推荐", type="primary",
                     use_container_width=True):
            set_student(Student(
                score=float(qscore), rank=int(est_rank or 50000),
                province=qp, subject_type=qs, electives=list(electives),
                city_prefs=city_prefs, major_prefs=major_prefs,
                level_pref=None if level_pref == "不限" else level_pref,
                family_economy="" if family_economy == "不便透露" else family_economy,
                accept_postgrad=(accept_postgrad == "接受"),
                career_intent="" if career_intent == "还没想好" else career_intent))
            st.switch_page(recommend_page)

    # 卡片外的次要入口：小字，不抢主按钮风头
    s1, s2 = st.columns(2)
    with s1:
        st.page_link(info_page, label="用完整表单填", icon="📝")
    with s2:
        if st.button("🎲 先用示例考生体验", use_container_width=True):
            sub0 = (available_subjects(st.session_state.get("home_prov")
                                       or available_provinces()[0]) or ["物理"])[0]
            set_student(Student(
                score=573, rank=50000,
                province=st.session_state.get("home_prov") or available_provinces()[0],
                subject_type=sub0,
                electives=["物理", "化学", "生物"] if sub0 == "综合" else []))
            st.switch_page(recommend_page)


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
