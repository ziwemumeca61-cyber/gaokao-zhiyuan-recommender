"""志愿诊断：把你的意向志愿（心愿单）整体体检，给出合理化建议。"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao import electives as el  # noqa: E402
from gaokao.data_loader import load_admissions  # noqa: E402
from gaokao.recommender import ml_model, rank_based  # noqa: E402
from gaokao.recommender.history import aggregate  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_scope_banner, require_student, wishlist_items,
)

st.title("🩺 志愿诊断")
st.caption("把你的意向志愿（心愿单）整体体检：梯度合不合理、保底够不够、有没有报不了或够不着的。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

items = wishlist_items()
if not items:
    st.info("心愿单是空的～ 先去 **🎯 志愿推荐 / 🃏 卡片选校 / 🏛️ 院校查询** 把意向专业加进来，再回来诊断。")
    st.page_link("pages/3_🎯_志愿推荐.py", label="➡️ 去志愿推荐", icon="🎯")
    st.stop()

stats = aggregate(load_admissions(), student.province, student.subject_type)

rows, evals = [], []
for school, major in items:
    stat = stats.get((school.id, major.id)) if school else None
    ok = el.satisfies(major.subject_req, student.electives)
    if stat:
        p, _lo, _hi = ml_model.predict_interval(
            student.rank, stat.ref_rank, stat.trend, rank_cv=stat.rank_cv,
            years=stat.years, plan=stat.total_plan, plan_ratio=stat.plan_ratio)
        tier = rank_based.classify(student.rank, stat.ref_rank) or "区间外"
        evals.append({"ok": ok, "data": True, "p": p, "tier": tier})
        status = "⛔不符选科" if not ok else "✅"
        rows.append({
            "院校·专业": f"{school.name}·{major.name}",
            "状态": status, "冲稳保": tier,
            "录取概率": f"{p * 100:.0f}%", "参考位次": stat.ref_rank,
            "选科要求": el.requirement_label(major.subject_req),
        })
    else:
        evals.append({"ok": ok, "data": False, "p": 0.0, "tier": "—"})
        rows.append({
            "院校·专业": f"{(school.name if school else '未知')}·{major.name}",
            "状态": "⚠️无数据", "冲稳保": "—", "录取概率": "—", "参考位次": "—",
            "选科要求": el.requirement_label(major.subject_req),
        })

st.markdown(f"#### 你的意向志愿（共 {len(items)} 个）")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------- 诊断结论 ----------
st.markdown("#### 🩺 诊断与建议")
data_ev = [e for e in evals if e["data"]]
n_bao = sum(1 for e in data_ev if e["tier"] == "保")
n_chong = sum(1 for e in data_ev if e["tier"] in ("冲", "区间外"))
n_safe = sum(1 for e in data_ev if e["p"] >= 0.8)
n_low = sum(1 for e in data_ev if e["p"] < 0.10)
n_subj = sum(1 for e in evals if not e["ok"])
n_nodata = sum(1 for e in evals if not e["data"])
seen = Counter((s.id if s else "", m.id) for s, m in items)
n_dup = sum(1 for v in seen.values() if v > 1)

issues = 0
if n_subj:
    st.error(f"⛔ 有 {n_subj} 个**不符合你的选科要求**，无法填报，请移除或替换。")
    issues += 1
if n_nodata:
    st.warning(f"⚠️ 有 {n_nodata} 个在「{student.province}·{student.subject_type}」下**查不到录取数据**，"
               "可能省份/科类不符或为新增专业，请核实。")
    issues += 1
if n_dup:
    st.warning(f"🔁 有 {n_dup} 组**重复志愿**，建议去重。")
    issues += 1
if n_low:
    st.error(f"🔴 有 {n_low} 个**录取概率很低（<10%）**，基本够不着，建议替换为更稳的。")
    issues += 1
if n_safe < 2:
    st.warning(f"🛡️ **保底偏少**（把握≥80% 的只有 {n_safe} 个），建议再补 2~3 个稳妥志愿，谨防滑档。")
    issues += 1
if n_chong == 0 and len(data_ev) >= 3:
    st.info("🚀 你的意向**全是稳/保**，在保底充足的前提下，可适当加 1~2 个冲一冲的好学校。")
if issues == 0:
    st.success("✅ 你的意向志愿**梯度合理、保底充足、选科匹配**，整体不错！建议按"
               "冲→稳→保的顺序排好，去『❤️ 我的志愿表』调整并导出。")

st.page_link("pages/8_❤️_我的志愿表.py", label="➡️ 去『我的志愿表』排序并导出", icon="❤️")
st.caption("诊断基于你省份科类的历年录取数据测算，仅供参考；正式填报以官方招生章程为准。")
