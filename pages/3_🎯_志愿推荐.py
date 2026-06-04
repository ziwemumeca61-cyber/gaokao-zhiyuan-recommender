"""志愿推荐：冲稳保三档志愿表 + 专业科普 + 一键导出推荐理由文档。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import report  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_major_detail, render_scope_banner, require_student,
    scope_label, school_caption, wishlist_button,
)

st.set_page_config(page_title="志愿推荐", page_icon="🎯", layout="wide")
st.title("🎯 志愿推荐")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

per_tier = st.slider("每档推荐数量", 3, 15, 8)
buckets = engine.recommend(student, per_tier=per_tier)
st.session_state["recommendations"] = buckets

total = sum(len(buckets[t]) for t in TIERS)
if total == 0:
    st.warning("没有匹配到合适的志愿，试试调整分数/位次或偏好。")
    st.stop()

# ---------- 一键导出 ----------
st.markdown("#### 📄 一键导出推荐理由文档")
md = report.build_markdown_report(student, buckets)
cols = st.columns(4)
with cols[0]:
    st.download_button("⬇️ Markdown", md, file_name="志愿推荐报告.md",
                       mime="text/markdown", use_container_width=True)
with cols[1]:
    if report.docx_available():
        st.download_button(
            "⬇️ Word", report.build_docx_report(student, buckets),
            file_name="志愿推荐报告.docx", use_container_width=True,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        st.button("Word（需 python-docx）", disabled=True, use_container_width=True)
with cols[2]:
    if report.pdf_available():
        st.download_button(
            "⬇️ PDF", report.build_pdf_report(student, buckets),
            file_name="志愿推荐报告.pdf", mime="application/pdf",
            use_container_width=True)
    else:
        st.button("PDF（需 reportlab）", disabled=True, use_container_width=True)
with cols[3]:
    with st.popover("👀 预览", use_container_width=True):
        st.markdown(md)

st.divider()

# ---------- 冲稳保三列 ----------
tier_help = {"冲": "🚀 冲一冲：略高于你的位次", "稳": "🎯 稳一稳：与你位次相近",
             "保": "🛡️ 保一保：你有明显优势"}
columns = st.columns(3)
for col, tier in zip(columns, TIERS):
    with col:
        recs = buckets[tier]
        st.markdown(f"### {tier}（{len(recs)}）")
        st.caption(tier_help[tier])
        for rec in recs:
            with st.container(border=True):
                st.markdown(f"**{rec.school.name} · {rec.major.name}**")
                st.caption(school_caption(rec.school))
                st.progress(
                    rec.probability,
                    text=f"录取概率 {rec.probability * 100:.0f}%"
                         f"（{rec.prob_low * 100:.0f}–{rec.prob_high * 100:.0f}%）")
                st.caption(f"📍{scope_label(student)}｜把握度 {rec.confidence}"
                           f"｜参考位次 {rec.ref_rank}｜参考分 {rec.ref_score}"
                           f"｜综合分 {rec.composite_score:.2f}")
                for reason in rec.reasons:
                    st.markdown(f"- {reason}")
                with st.expander("📚 这个专业是干嘛的？"):
                    render_major_detail(rec.major)
                wishlist_button(rec.major, key=f"wish_rec_{tier}_{rec.major.id}")
