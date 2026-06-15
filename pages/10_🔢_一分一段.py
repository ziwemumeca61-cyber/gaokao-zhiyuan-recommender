"""一分一段：分数⇄位次双向换算，帮考生把"分数"和"位次"对齐，减少填错。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao import rank_score  # noqa: E402
from gaokao.data_loader import available_provinces  # noqa: E402
from gaokao.models import RIASEC_DIMENSIONS, Student  # noqa: E402
from gaokao.ui_helpers import ensure_data, get_student, set_student  # noqa: E402

st.title("🔢 一分一段换算")
st.caption("分数和位次是一回事的两种说法。高考按省划线，换算只在同省同科类内有意义。")

if not ensure_data():
    st.stop()

student = get_student()
# 省份候选 = 录取数据里的省份 ∪ 有真实一分一段种子的省份
provinces = sorted(set(available_provinces()) | set(rank_score.segment_provinces()))

# ---------- 省份/科类（科类随省份动态：3+3 省份为"综合"） ----------
c1, c2 = st.columns(2)
with c1:
    p_idx = provinces.index(student.province) if student and student.province in provinces else 0
    province = st.selectbox("生源所在省份", provinces, index=p_idx)
with c2:
    seg_subjects = [s for (p, s) in rank_score.segment_pairs() if p == province]
    subjects = (["物理", "历史"] if province in available_provinces() else [])
    for s in seg_subjects:
        if s not in subjects:
            subjects.append(s)
    subjects = subjects or ["物理", "历史"]
    s_idx = subjects.index(student.subject_type) if (
        student and student.subject_type in subjects) else 0
    subject = st.radio("选科科类", subjects, index=s_idx, horizontal=True)

if subject == "综合":
    st.info(f"📍 {province} 为 3+3 模式，不分物理/历史，采用**全省统一**的综合一分一段。"
            "高考按省份分别划线，跨省的分数/位次不可直接换算或比较。")
else:
    st.info(f"📍 以下换算基于 **{province} · {subject}** 的数据。"
            "高考按省份分别划线，跨省的分数/位次不可直接换算或比较。")

table = rank_score.build_table(province, subject)
if table is None:
    st.warning(f"{province} · {subject} 的数据不足，暂无法换算。")
    st.stop()

if table.source.is_real:
    link = f"（[来源]({table.source.url})）" if table.source.url else ""
    st.success(f"✅ 真实数据：{table.source.label}{link}")
else:
    st.warning("⚠️ 本省该科类暂无真实一分一段，下列换算基于**模拟数据**推导，仅供演示。")
st.caption(f"实测覆盖：分数 {table.score_min}~{table.score_max} 分"
           f"｜位次 {table.rank_best}~{table.rank_worst}。超出部分按趋势估算。")


def _note(conv) -> None:
    if conv.clamped:
        st.caption("⚠️ 超出实测分数段，结果为按趋势外推的**估算值**，仅供参考。")


# ---------- 换算（单一输入，避免两个方向自相矛盾） ----------
_smax = 900 if table.score_max > 750 else 750
mode = st.radio("你手上有哪个？", ["📊 我知道分数", "🔢 我知道位次"], horizontal=True)
if mode == "📊 我知道分数":
    _sdefault = min(max(int(student.score) if student else 600, 0), _smax)
    score_val = st.number_input("输入高考分数", min_value=0, max_value=_smax,
                                value=_sdefault, step=1)
    conv = table.rank_for_score(score_val)
    rank_val = conv.value
    st.metric(f"{int(score_val)} 分　→　对应全省位次", f"{rank_val:,}")
else:
    _rdefault = min(max(int(student.rank) if student else 15000, 1), 900000)
    rank_val = st.number_input("输入全省位次", min_value=1, max_value=900000,
                               value=_rdefault, step=1)
    conv = table.score_for_rank(rank_val)
    score_val = conv.value
    st.metric(f"位次 {int(rank_val):,}　→　对应高考分数", f"{score_val} 分")
    st.caption("注：一个分数对应一段位次区间，把这个分数再换回位次可能差几名，属正常。")
_note(conv)
score_val, rank_val = int(score_val), int(rank_val)

# ---------- 应用到我的信息 ----------
st.divider()
st.markdown("#### 一键写入我的信息")
st.caption("把上面这组分数+位次写入考生画像，志愿推荐会据此计算。")


def _apply(score: int, rank: int) -> None:
    existing = get_student()
    new = Student(score=float(score), rank=int(rank), province=province,
                  subject_type=subject)
    if existing:
        new.city_prefs = existing.city_prefs
        new.major_prefs = existing.major_prefs
        new.level_pref = existing.level_pref
        if existing.has_assessment():
            new.riasec = dict(existing.riasec)
    else:
        new.riasec = {d: 0.0 for d in RIASEC_DIMENSIONS}
    set_student(new)


if st.button(f"✅ 写入：分数 {score_val} ｜ 位次 {rank_val:,}", type="primary"):
    _apply(score_val, rank_val)
    st.success(f"已写入：{province}·{subject}，分数 {score_val}，位次 {rank_val:,}。")

# ---------- 曲线 ----------
st.divider()
st.markdown("#### 📈 分数—位次曲线")
pts = table.points()
fig = go.Figure()
fig.add_trace(go.Scatter(x=[s for s, _ in pts], y=[r for _, r in pts],
                         mode="lines", name="一分一段", line_color="#1FA463"))
fig.add_trace(go.Scatter(x=[score_val], y=[rank_val], mode="markers",
                         name="你的位置", marker=dict(size=12, color="#00A699")))
fig.update_yaxes(autorange="reversed", title="全省位次（越小越好）")
fig.update_xaxes(title="高考分数")
fig.update_layout(height=420, legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, use_container_width=True)
