"""卡片选校：像刷卡片一样挑学校，👍 喜欢进心愿单，👎 跳过。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import load_majors  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, get_wishlist, render_major_detail, require_student,
    school_caption, toggle_wishlist,
)

st.set_page_config(page_title="卡片选校", page_icon="🃏", layout="centered")
st.title("🃏 卡片选校")
st.caption("一张张来，喜欢就 ❤️，不感冒就 👉。喜欢的会进入心愿单。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()


def _build_deck():
    buckets = engine.recommend(student, per_tier=12)
    deck = []
    for tier in TIERS:
        for rec in buckets[tier]:
            deck.append(rec)
    deck.sort(key=lambda r: r.composite_score, reverse=True)
    return deck


if "card_deck" not in st.session_state or st.button("🔄 重新洗牌"):
    st.session_state["card_deck"] = _build_deck()
    st.session_state["card_idx"] = 0

deck = st.session_state["card_deck"]
idx = st.session_state.get("card_idx", 0)

st.progress(min(idx / max(len(deck), 1), 1.0),
            text=f"已浏览 {min(idx, len(deck))}/{len(deck)}　❤️ 心愿单 {len(get_wishlist())}")

if idx >= len(deck):
    st.success("🎉 看完啦！去 **📊 数据大屏** 或 **🎯 志愿推荐** 看看你的心愿单吧。")
    st.stop()

rec = deck[idx]
with st.container(border=True):
    tier_emoji = {"冲": "🚀", "稳": "🎯", "保": "🛡️"}[rec.tier]
    st.markdown(f"### {rec.school.name}")
    st.markdown(f"#### {rec.major.name}　{tier_emoji}{rec.tier}")
    st.caption(school_caption(rec.school))
    st.progress(rec.probability, text=f"录取概率 {rec.probability * 100:.0f}%")
    if rec.major.intro:
        st.markdown(f"💡 {rec.major.intro}")
    if rec.major.career_paths:
        st.markdown("**就业方向**：" + "、".join(rec.major.career_paths))
    with st.expander("📚 看看完整专业科普"):
        render_major_detail(rec.major)


def _advance(like: bool):
    if like:
        if rec.major.id not in get_wishlist():
            toggle_wishlist(rec.major.id)
    st.session_state["card_idx"] = idx + 1


c1, c2 = st.columns(2)
with c1:
    st.button("👉 跳过", use_container_width=True, on_click=_advance, args=(False,))
with c2:
    st.button("❤️ 喜欢", type="primary", use_container_width=True,
              on_click=_advance, args=(True,))

# 心愿单一览
wl = get_wishlist()
if wl:
    st.divider()
    st.markdown("#### ❤️ 我的心愿单")
    majors = load_majors()
    for mid in wl:
        m = majors.get(mid)
        if m:
            st.markdown(f"- {m.name}　`{m.category}`")
