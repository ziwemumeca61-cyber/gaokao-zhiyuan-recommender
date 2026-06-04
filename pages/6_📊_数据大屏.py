"""数据大屏：用交互图表把推荐结果、概率、兴趣、热度一图看懂。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao.data_loader import load_admissions, load_majors  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine, trending  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_scope_banner, require_student, riasec_radar, scope_label,
)

st.set_page_config(page_title="数据大屏", page_icon="📊", layout="wide")
st.title("📊 数据大屏")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

buckets = engine.recommend(student, per_tier=12)
flat = [r for t in TIERS for r in buckets[t]]
if not flat:
    st.warning("暂无推荐数据，调整信息后再来。")
    st.stop()

# 第一行：冲稳保结构 + 录取概率分布
r1c1, r1c2 = st.columns(2)
with r1c1:
    st.markdown("#### 志愿冲稳保结构")
    counts = {t: len(buckets[t]) for t in TIERS}
    fig = px.pie(names=list(counts.keys()), values=list(counts.values()),
                 color=list(counts.keys()),
                 color_discrete_map={"冲": "#FF5A5F", "稳": "#FFB400", "保": "#00A699"})
    st.plotly_chart(fig, use_container_width=True)
with r1c2:
    st.markdown(f"#### 录取概率分布（{scope_label(student)}）")
    probs = [r.probability * 100 for r in flat]
    fig = px.histogram(x=probs, nbins=10, labels={"x": "录取概率(%)", "y": "志愿数"})
    fig.update_traces(marker_color="#FF5A5F")
    st.plotly_chart(fig, use_container_width=True)

# 第二行：兴趣雷达 + 专业热度榜
r2c1, r2c2 = st.columns(2)
with r2c1:
    st.markdown("#### 你的兴趣画像")
    if student.has_assessment():
        st.plotly_chart(riasec_radar(student.riasec), use_container_width=True)
    else:
        st.info("还没做兴趣测评，去 🧭 兴趣测评 解锁雷达图。")
with r2c2:
    st.markdown("#### 热门专业 Top 10")
    trends = trending.rank_hot_majors(load_majors(), top_n=10)
    fig = px.bar(x=[t.score for t in trends][::-1],
                 y=[t.name for t in trends][::-1], orientation="h",
                 labels={"x": "综合热度", "y": ""})
    fig.update_traces(marker_color="#00A699")
    st.plotly_chart(fig, use_container_width=True)

# 第三行：位次走势
st.markdown(f"#### 院校专业录取位次走势（{scope_label(student)}）")
options = {f"{r.school.name} · {r.major.name}": (r.school.id, r.major.id)
           for r in flat}
choice = st.selectbox("选择一个推荐查看历年位次", list(options.keys()))
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
    fig.update_yaxes(autorange="reversed")  # 位次越小越靠上
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("该专业暂无历年位次数据。")
