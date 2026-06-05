"""数据大屏：用图表把你的推荐结果讲清楚——梯度、院校层次、概率、历年位次。"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao.data_loader import load_admissions  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_scope_banner, require_student, riasec_radar,
)

st.title("📊 数据大屏")
st.caption("把你的推荐结果用图表讲清楚：志愿梯度、院校层次、录取概率、历年位次走势。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

buckets = engine.recommend(student, per_tier=12)
flat = [r for t in TIERS for r in buckets[t]]
if not flat:
    st.warning("暂无推荐数据，去 📝 信息录入 调整分数/位次后再来。")
    st.stop()

# ---------- 概览 ----------
m = st.columns(4)
m[0].metric("推荐总数", len(flat))
m[1].metric("🔴 冲", len(buckets["冲"]))
m[2].metric("🟡 稳", len(buckets["稳"]))
m[3].metric("🟢 保", len(buckets["保"]))

st.divider()

# ---------- 第一行：志愿梯度 + 院校层次 ----------
r1c1, r1c2 = st.columns(2)
with r1c1:
    st.markdown("#### 🎯 志愿梯度（冲 / 稳 / 保）")
    st.caption("一份好的志愿表要有梯度：冲一冲、稳一稳、保一保。看比例是否均衡。")
    counts = {t: len(buckets[t]) for t in TIERS}
    fig = px.pie(names=list(counts.keys()), values=list(counts.values()),
                 color=list(counts.keys()),
                 color_discrete_map={"冲": "#FF5A5F", "稳": "#FFB400", "保": "#00A699"})
    fig.update_traces(textinfo="label+value")
    st.plotly_chart(fig, use_container_width=True)
with r1c2:
    st.markdown("#### 🏫 推荐里的院校层次")
    st.caption("你的推荐院校中，985 / 211 / 双一流 / 普通各有多少所。")
    lv = Counter(r.school.level for r in flat)
    order = [k for k in ["985", "211", "双一流", "普通"] if k in lv] + \
            [k for k in lv if k not in ("985", "211", "双一流", "普通")]
    fig = px.bar(x=[lv[k] for k in order], y=order, orientation="h",
                 labels={"x": "院校数", "y": "层次"}, text=[lv[k] for k in order])
    fig.update_traces(marker_color="#FF5A5F")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- 第二行：录取概率分布 + 兴趣画像 ----------
r2c1, r2c2 = st.columns(2)
with r2c1:
    st.markdown("#### 📈 录取概率分布")
    st.caption("每根柱子＝落在该概率区间的志愿数。柱子越靠右，说明越多志愿你较有把握。")
    probs = [r.probability * 100 for r in flat]
    fig = px.histogram(x=probs, nbins=10, labels={"x": "录取概率(%)", "y": "志愿数量"})
    fig.update_traces(marker_color="#00A699")
    st.plotly_chart(fig, use_container_width=True)
with r2c2:
    st.markdown("#### 🧭 你的兴趣画像")
    st.caption("霍兰德六维兴趣雷达，面积越偏向某维，越适合相关专业方向。")
    if student.has_assessment():
        st.plotly_chart(riasec_radar(student.riasec), use_container_width=True)
    else:
        st.info("还没做兴趣测评 → 去 🧭 兴趣测评 解锁你的兴趣雷达图。")

st.divider()

# ---------- 第三行：历年录取位次走势 ----------
st.markdown("#### 📉 某个推荐的历年录取位次走势")
st.caption("选一个推荐，看它近几年的最低录取位次。绿色虚线是你的位次——"
           "**红线在绿线下方（位次更小）说明门槛更高、你需要冲**；在上方则更有把握。位次越小越靠上。")
options = {f"{r.school.name} · {r.major.name}": (r.school.id, r.major.id) for r in flat}
choice = st.selectbox("选择一个推荐", list(options.keys()))
sid, mid = options[choice]
records = [r for r in load_admissions()
           if r.school_id == sid and r.major_id == mid
           and r.province == student.province
           and r.subject_type == student.subject_type]
records.sort(key=lambda r: r.year)
if records:
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
