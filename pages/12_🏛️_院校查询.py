"""院校查询：搜一所学校，看它在你省份科类下的全部专业录取线、概率与选科要求。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao import electives as el  # noqa: E402
from gaokao.data_loader import load_admissions, load_majors, load_schools  # noqa: E402
from gaokao.recommender import ml_model, rank_based  # noqa: E402
from gaokao.recommender.history import aggregate  # noqa: E402
from gaokao.ui_helpers import ensure_data, render_scope_banner, require_student  # noqa: E402

st.title("🏛️ 院校查询")
st.caption("选一所学校，看它在你的省份+科类下，每个专业近年录取位次、你的录取概率和选科要求。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

schools = load_schools()
majors = load_majors()
stats = aggregate(load_admissions(), student.province, student.subject_type)

# 只列出在该省该科类有招生数据的院校
sids_with_data = {sid for (sid, _mid) in stats}
options = sorted(
    (s for s in schools.values() if s.id in sids_with_data),
    key=lambda s: s.name)
if not options:
    st.warning("当前省份+科类下暂无院校数据。")
    st.stop()

labels = {f"{s.name}（{s.city}·{s.level}）": s.id for s in options}
choice = st.selectbox("选择 / 搜索院校", list(labels.keys()))
sid = labels[choice]
school = schools[sid]

st.markdown(f"### {school.name}")
st.caption(f"{school.province} · {school.city}　|　{school.level} · {school.type}")

# 该校在此省此科类的所有专业
rows = []
for (s_id, m_id), stat in stats.items():
    if s_id != sid:
        continue
    m = majors.get(m_id)
    if m is None:
        continue
    p, lo, hi = ml_model.predict_interval(
        student.rank, stat.ref_rank, stat.trend, rank_cv=stat.rank_cv,
        years=stat.years, plan=stat.total_plan, plan_ratio=stat.plan_ratio)
    tier = rank_based.classify(student.rank, stat.ref_rank) or "—"
    ok = el.satisfies(m.subject_req, student.electives)
    rows.append({
        "专业": m.name,
        "能否报": "✅" if ok else "❌不符选科",
        "选科要求": el.requirement_label(m.subject_req),
        "参考位次": stat.ref_rank,
        "参考分": stat.ref_score,
        "录取概率": f"{p * 100:.0f}%",
        "冲稳保": tier,
    })

if not rows:
    st.info("该校在此省此科类暂无专业数据。")
    st.stop()

df = pd.DataFrame(rows).sort_values("参考位次").reset_index(drop=True)
st.markdown(f"共 **{len(df)}** 个专业（按参考位次从高到低排序；位次越小越难）。")
only_ok = st.checkbox("只看我能报的（符合选科）", value=bool(student.electives))
if only_ok and student.electives:
    df = df[df["能否报"] == "✅"]
st.dataframe(df, use_container_width=True, hide_index=True)
st.caption("录取概率＝拿你的位次与该专业近年录取线（含历年波动）比算得；冲/稳/保为相对你位次的档位。")
