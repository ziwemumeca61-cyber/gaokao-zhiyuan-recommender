"""志愿体检：用大白话告诉考生——这份推荐怎么样、有什么风险、下一步该干嘛。"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import load_admissions  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import ensure_data, render_scope_banner, require_student  # noqa: E402

st.title("📋 志愿体检")
st.caption("不堆图表，直接用大白话告诉你：这份推荐合不合理、有什么风险、接下来该做什么。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

buckets = engine.recommend(student, per_tier=10)
flat = [r for t in TIERS for r in buckets[t]]
if not flat:
    st.warning("暂时没匹配到合适的志愿，去 📝 信息录入 调整分数/位次或选考科目后再来。")
    st.stop()

n_chong, n_wen, n_bao = (len(buckets["冲"]), len(buckets["稳"]), len(buckets["保"]))

# ---------- 1. 冲稳保梯度 ----------
with st.container(border=True):
    st.markdown("### 1️⃣ 你的志愿梯度")
    st.markdown(f"系统给你找到：🔴 **冲 {n_chong} 个**、🟡 **稳 {n_wen} 个**、🟢 **保 {n_bao} 个**。")
    if n_bao < 3:
        st.error("⚠️ **保底太少了**。保底志愿是你的「安全垫」，建议至少留 3~5 个很有把握的，"
                 "否则有滑档风险。去『🃏 卡片选校』或『🎯 志愿推荐』多挑几个保底专业。")
    elif n_chong == 0:
        st.warning("你**没有冲刺志愿**。在保底充足的前提下，可以加 1~2 个「冲一冲」的好学校，"
                   "万一录上就赚了。")
    else:
        st.success("✅ **梯度比较合理**：有冲有稳有保。建议把更有把握的放在志愿表靠前位置。")

# ---------- 2. 录取把握 ----------
with st.container(border=True):
    st.markdown("### 2️⃣ 录取把握怎么样")
    n_safe = sum(1 for r in flat if r.probability >= 0.8)
    n_risky = sum(1 for r in flat if r.probability < 0.4)
    avg = sum(r.probability for r in flat) / len(flat)
    st.markdown(f"在这 {len(flat)} 个推荐里，**{n_safe} 个比较稳妥**（录取概率≥80%）、"
                f"**{n_risky} 个偏冒险**（＜40%）；平均录取概率约 **{avg * 100:.0f}%**。")
    if n_safe < 3:
        st.warning("稳妥的志愿偏少。建议多保留几个录取概率高的，让志愿表更安全。")
    else:
        st.success("✅ 有足够多把握大的志愿垫底，整体比较稳。")
    st.caption("说明：录取概率＝拿你的位次和这个专业近几年录取线比，并考虑了历年波动算出来的。")

# ---------- 3. 院校层次 ----------
with st.container(border=True):
    st.markdown("### 3️⃣ 推荐里的院校层次")
    lv = Counter(r.school.level for r in flat)
    parts = [f"**{lv[k]} 所 {k}**" for k in ["985", "211", "双一流", "普通"] if lv.get(k)]
    other = [f"**{lv[k]} 所 {k}**" for k in lv if k not in ("985", "211", "双一流", "普通")]
    st.markdown("你够得着的层次：" + "、".join(parts + other) + "。")
    if lv.get("985") or lv.get("211"):
        st.success("✅ 推荐里有重点院校（985/211），优先关注这些。")
    else:
        st.info("以普通本科为主——可在保底充足时，加一两个稍冲的好学校试试。")

# ---------- 4. 下一步建议 ----------
with st.container(border=True):
    st.markdown("### 4️⃣ 接下来怎么做")
    st.markdown("1. 去 **🎯 志愿推荐** 把心仪的专业 ❤️ 加入心愿单；\n"
                "2. 到 **❤️ 我的志愿表** 把它们按「冲→稳→保」排好顺序；\n"
                "3. 用 **🆚 院校对比** 在几个纠结的之间做选择；\n"
                "4. 最后从『我的志愿表』**一键导出** PDF/Word 拿去参考填报。")
    c1, c2 = st.columns(2)
    c1.page_link("pages/3_🎯_志愿推荐.py", label="去看志愿推荐", icon="🎯")
    c2.page_link("pages/8_❤️_我的志愿表.py", label="去整理我的志愿表", icon="❤️")

# ---------- 可选：历年位次走势（想看才展开） ----------
with st.expander("📈 想看某个推荐近几年的录取位次走势？点这里"):
    st.caption("红线＝该专业近几年的最低录取位次；绿色虚线＝你的位次。"
               "红线在绿线**下方**（位次更小）＝门槛更高、要冲；在上方＝更有把握。")
    options = {f"{r.school.name} · {r.major.name}": (r.school.id, r.major.id) for r in flat}
    choice = st.selectbox("选择一个推荐", list(options.keys()))
    sid, mid = options[choice]
    records = sorted(
        (r for r in load_admissions()
         if r.school_id == sid and r.major_id == mid
         and r.province == student.province and r.subject_type == student.subject_type),
        key=lambda r: r.year)
    if records:
        import plotly.express as px  # noqa: PLC0415

        fig = px.line(x=[r.year for r in records], y=[r.min_rank for r in records],
                      markers=True, labels={"x": "年份", "y": "最低录取位次"})
        fig.update_traces(line_color="#FF5A5F")
        fig.add_hline(y=student.rank, line_dash="dash", line_color="#00A699",
                      annotation_text=f"你的位次 {student.rank}")
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("该专业暂无历年位次数据。")
