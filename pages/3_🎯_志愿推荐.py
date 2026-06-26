"""志愿推荐：冲稳保三档志愿表 + 专业科普 + 一键导出推荐理由文档。"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import assessment, report  # noqa: E402
from gaokao.major_knowledge import heat_for  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_major_detail, render_scope_banner, require_student,
    scope_label, school_caption, wishlist_button,
)

st.title("🎯 志愿推荐")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

from gaokao import control_lines  # noqa: E402

_cl = control_lines.describe(student.province, student.subject_type, int(student.score))
if _cl:
    st.info(f"📏 你 {int(student.score)}分　{_cl}")

c1, c2 = st.columns([2, 1])
with c1:
    mode = st.radio("推荐方式", ["🎯 综合推荐", "🧭 按兴趣推荐", "🔥 热门推荐"],
                    horizontal=True,
                    help="综合=概率+兴趣+偏好均衡；按兴趣=侧重你测评的兴趣方向；"
                         "热门=把公认的热门专业往前排")
with c2:
    per_tier = st.slider("每档数量", 3, 15, 8)

# 兴趣偏好：用兴趣测评得出的建议门类（没测评则用你填的意向门类）
interest_cats: list[str] = []
if student.has_assessment():
    interest_cats = assessment.suggested_categories(student.riasec)
elif student.major_prefs:
    interest_cats = list(student.major_prefs)

if mode == "🧭 按兴趣推荐":
    if not interest_cats:
        st.info("想用『按兴趣推荐』更准，建议先做 **🧭 兴趣测评**（或在信息录入选意向门类）。"
                "暂未测评，下面先按综合方式展示。")
        buckets = engine.recommend(student, per_tier=per_tier)
    else:
        st.caption("📌 已侧重你的兴趣方向：" + "、".join(interest_cats))
        # 兴趣模式：把建议门类作为偏好，并加大兴趣/门类权重
        s2 = replace(student, major_prefs=interest_cats)
        w = {"probability": 0.30, "interest": 0.34, "heat": 0.04,
             "city": 0.06, "level": 0.06, "category": 0.20}
        buckets = engine.recommend(s2, per_tier=per_tier, weights=w)
elif mode == "🔥 热门推荐":
    st.caption("📌 已把公认的热门专业（计算机/临床/金融等）往前排，仍按你的位次冲稳保。")
    pool = engine.recommend(student, per_tier=per_tier * 4)
    buckets = {}
    for t in TIERS:
        ranked = sorted(
            pool[t],
            key=lambda r: (heat_for(r.major.name, r.major.category), r.composite_score),
            reverse=True)
        buckets[t] = ranked[:per_tier]
else:
    buckets = engine.recommend(student, per_tier=per_tier)

st.session_state["recommendations"] = buckets

total = sum(len(buckets[t]) for t in TIERS)
if total == 0:
    st.warning("没有匹配到合适的志愿，试试调整分数/位次或偏好。")
    st.stop()

# ---------- 筛选（按院校层次 / 学科门类） ----------
with st.expander("🔎 筛选推荐结果"):
    _levels = sorted({r.school.level for t in TIERS for r in buckets[t]})
    _cats = sorted({r.major.category for t in TIERS for r in buckets[t]})
    fc1, fc2 = st.columns(2)
    sel_levels = fc1.multiselect("院校层次", _levels)
    sel_cats = fc2.multiselect("学科门类", _cats)
if sel_levels or sel_cats:
    buckets = {
        t: [r for r in buckets[t]
            if (not sel_levels or r.school.level in sel_levels)
            and (not sel_cats or r.major.category in sel_cats)]
        for t in TIERS}
    if sum(len(buckets[t]) for t in TIERS) == 0:
        st.warning("当前筛选条件下没有结果，放宽筛选试试。")
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
        st.download_button(
            "⬇️ Word(.rtf)", report.build_rtf_report(student, buckets),
            file_name="志愿推荐报告.rtf", mime="application/rtf",
            use_container_width=True, help="RTF 格式，Word/WPS 可直接打开")
with cols[2]:
    if report.pdf_available():
        st.download_button(
            "⬇️ PDF", report.build_pdf_report(student, buckets),
            file_name="志愿推荐报告.pdf", mime="application/pdf",
            use_container_width=True)
    else:
        st.download_button(
            "⬇️ PDF(网页版)", report.build_html_report(student, buckets),
            file_name="志愿推荐报告.html", mime="text/html",
            use_container_width=True, help="下载后用浏览器打开，按 Ctrl/⌘+P 另存为 PDF")
with cols[3]:
    with st.popover("👀 预览", use_container_width=True):
        st.markdown(md)

st.divider()

# ---------- 冲稳保三列 ----------
tier_help = {"冲": "🚀 冲一冲：略高于你的位次", "稳": "🎯 稳一稳：与你位次相近",
             "保": "🛡️ 保一保：你有明显优势"}
# 空档位的友好提示（按风险给不同口吻；保底为空最危险）
tier_empty = {
    "冲": "ℹ️ 当前科类/位次暂无合适的冲刺项，建议把精力放在稳、保两档。",
    "稳": "ℹ️ 暂无稳妥项，注意把冲与保搭配好，避免梯度断层。",
    "保": "⚠️ 暂无保底项！请务必再补充几个有把握的志愿，谨防滑档。",
}
columns = st.columns(3)
for col, tier in zip(columns, TIERS):
    with col:
        recs = buckets[tier]
        st.markdown(f"### {tier}（{len(recs)}）")
        st.caption(tier_help[tier])
        if not recs:
            if tier == "保":
                st.warning(tier_empty[tier])
            else:
                st.info(tier_empty[tier])
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

st.divider()
st.markdown("##### 把心仪的 ❤️ 加进心愿单后，下一步：")
n1, n2 = st.columns(2)
n1.page_link("pages/6_📊_数据大屏.py", label="🩺 体检我选的志愿（看合不合理）", icon="📋")
n2.page_link("pages/8_❤️_我的志愿表.py", label="❤️ 整理顺序 / 一键导出", icon="❤️")
