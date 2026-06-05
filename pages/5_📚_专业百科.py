"""专业百科：把每个专业讲清楚——学什么、干什么、适合谁；含热门专业推荐。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import available_categories, load_majors  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine, trending  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, get_student, render_major_detail, school_caption, wishlist_button,
)

st.title("📚 专业百科")
st.caption("不知道专业是干嘛的？这里把每个专业讲明白：学什么课、将来干什么、适合什么样的人。")

if not ensure_data():
    st.stop()

majors = load_majors()
categories = ["全部", *available_categories()]

tab_hot, tab_browse = st.tabs(["🔥 热门专业推荐", "🔎 浏览 / 搜索专业"])

# ---------- 热门专业推荐 ----------
with tab_hot:
    c1, c2 = st.columns([1, 1])
    with c1:
        cat = st.selectbox("门类筛选", categories, key="hot_cat")
    with c2:
        top_n = st.slider("显示数量", 5, 30, 15, key="hot_n")
    cat_arg = None if cat == "全部" else cat
    trends = trending.rank_hot_majors(majors, category=cat_arg, top_n=top_n)
    for i, t in enumerate(trends, start=1):
        with st.expander(f"{i}. {t.name}　`{t.category}`　🔥{t.score:.0f}"
                         f"　就业 {t.avg_employment * 100:.0f}%　{t.count} 校开设"):
            render_major_detail(t.sample)
            wishlist_button(t.sample, key=f"wish_hot_{t.sample.id}")

    # 个性化：分数够得着的热门专业
    student = get_student()
    if student is not None:
        st.divider()
        st.markdown("### 🎯 分数够得着的热门专业（个性化）")
        st.caption("从热门榜里，筛出按你的位次能冲/能稳/能保的院校专业组合。")
        hot_names = trending.hot_major_names(majors, top_n=30)
        buckets = engine.recommend(student, per_tier=30)
        any_pick = False
        for tier in TIERS:
            picks = [r for r in buckets[tier] if r.major.name in hot_names][:6]
            if not picks:
                continue
            any_pick = True
            st.markdown(f"**{tier}**")
            for rec in picks:
                st.markdown(
                    f"- {rec.school.name} · **{rec.major.name}**"
                    f"（{school_caption(rec.school)}）"
                    f"｜录取概率 {rec.probability * 100:.0f}%")
        if not any_pick:
            st.info("当前位次下暂未匹配到热门专业，去 🎯 志愿推荐 看看全部选择吧。")
    else:
        st.info("填写 **📝 信息录入** 后，这里会显示'你分数够得着的热门专业'。")

# ---------- 浏览 / 搜索 ----------
with tab_browse:
    c1, c2 = st.columns([2, 1])
    with c1:
        kw = st.text_input("搜索专业名称", placeholder="如：计算机、临床医学、金融")
    with c2:
        bcat = st.selectbox("门类", categories, key="browse_cat")

    # 同名专业去重，取代表
    seen: dict[str, object] = {}
    for m in majors.values():
        if m.name not in seen:
            seen[m.name] = m
    items = list(seen.values())
    if kw:
        items = [m for m in items if kw.strip() in m.name]
    if bcat != "全部":
        items = [m for m in items if m.category == bcat]
    items.sort(key=lambda m: m.heat, reverse=True)

    st.caption(f"共 {len(items)} 个专业")
    for m in items[:60]:
        with st.expander(f"{m.name}　`{m.category}`　🔥{m.heat:.0f}"):
            render_major_detail(m)
            wishlist_button(m, key=f"wish_browse_{m.id}")
