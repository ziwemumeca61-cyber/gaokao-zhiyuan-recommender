"""院校对比：从心愿单/推荐里挑 2~4 个 院校·专业，并排比指标，辅助最终取舍。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import compare  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, get_wishlist, render_scope_banner, require_student,
    school_caption, wishlist_button,
)

st.title("🆚 院校对比")
st.caption("把纠结的几个 院校·专业 放一起比，一眼看清谁更稳、谁更合适。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)


# ---------- 候选池：心愿单 + 当前推荐，去重并保留可读标签 ----------
def _candidate_pool() -> dict[str, tuple[str, str]]:
    from gaokao.data_loader import load_majors, load_schools

    majors = load_majors()
    schools = load_schools()
    pool: dict[str, tuple[str, str]] = {}

    def _add(school_id: str, major_id: str) -> None:
        m = majors.get(major_id)
        s = schools.get(school_id)
        if m is None or s is None:
            return
        pool[f"{s.name} · {m.name}"] = (school_id, major_id)

    for mid in get_wishlist():
        m = majors.get(mid)
        if m is not None:
            _add(m.school_id, mid)
    buckets = st.session_state.get("recommendations") or {}
    for tier in TIERS:
        for r in buckets.get(tier, []):
            _add(r.school.id, r.major.id)
    return pool


pool = _candidate_pool()
if not pool:
    st.info("还没有可对比的候选。先到 **🎯 志愿推荐** 生成推荐，或把心仪专业加入 **❤️ 心愿单**。")
    st.page_link("pages/3_🎯_志愿推荐.py", label="➡️ 去志愿推荐", icon="🎯")
    st.page_link("pages/8_❤️_我的志愿表.py", label="➡️ 看我的志愿表", icon="❤️")
    st.stop()

labels = list(pool.keys())
default = labels[: min(3, len(labels))]
chosen = st.multiselect("选择要对比的 院校·专业（建议 2~4 个）", labels, default=default)

if len(chosen) < 2:
    st.warning("请至少选择 2 个进行对比。")
    st.stop()
if len(chosen) > 4:
    st.info("最多对比 4 个，已取前 4 个。")
    chosen = chosen[:4]

rows = compare.compare(student, [pool[label] for label in chosen])
if not rows:
    st.warning("所选候选暂无可用数据。")
    st.stop()


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# ---------- 顶部卡片：名称 + 档位 + 概率 ----------
tier_color = {"冲": "🔴 冲", "稳": "🟡 稳", "保": "🟢 保", "": "⚪ 区间外"}
cols = st.columns(len(rows))
best = compare.best_index(rows)
for i, (col, row) in enumerate(zip(cols, rows)):
    with col, st.container(border=True):
        crown = "👑 " if i == best else ""
        st.markdown(f"**{crown}{row.major.name}**")
        st.caption(school_caption(row.school))
        st.markdown(tier_color.get(row.tier, "⚪ 区间外"))
        if row.has_data:
            st.progress(row.probability,
                        text=f"录取概率 {_fmt_pct(row.probability)}"
                             f"（{_fmt_pct(row.prob_low)}–{_fmt_pct(row.prob_high)}）")
        else:
            st.caption("⚠️ 本省该科类暂无录取数据")
        wishlist_button(row.major, key=f"cmp_wish_{row.school.id}_{row.major.id}")

if best is not None:
    st.success(f"综合最优：**{rows[best].school.name} · {rows[best].major.name}**"
               f"（综合分 {rows[best].composite_score:.2f}）。综合分越高，越契合你的分数与偏好。")

st.divider()

# ---------- 并排指标表（指标为行，候选为列） ----------
col_names = [f"{r.school.name}·{r.major.name}" for r in rows]


def _row_vals(getter) -> list[str]:
    return [getter(r) if r.has_data else "—" for r in rows]


table = {
    "院校层次": [r.school.level for r in rows],
    "城市": [r.school.city for r in rows],
    "院校类型": [r.school.type for r in rows],
    "学科门类": [r.major.category for r in rows],
    "参考位次": _row_vals(lambda r: f"{r.ref_rank}"),
    "参考分数": _row_vals(lambda r: f"{r.ref_score}"),
    "位次比(你/校)": _row_vals(lambda r: f"{r.ratio:.2f}"),
    "冲稳保": [tier_color.get(r.tier, "⚪ 区间外") for r in rows],
    "录取概率": _row_vals(lambda r: _fmt_pct(r.probability)),
    "概率区间": _row_vals(lambda r: f"{_fmt_pct(r.prob_low)}–{_fmt_pct(r.prob_high)}"),
    "把握度": _row_vals(lambda r: r.confidence),
    "兴趣匹配": _row_vals(lambda r: _fmt_pct(r.interest_match)),
    "综合分": _row_vals(lambda r: f"{r.composite_score:.2f}"),
}
df = pd.DataFrame(table, index=col_names).T
st.markdown("#### 📋 指标对照表")
st.dataframe(df, use_container_width=True)

# ---------- 关键指标柱状图（仅有数据的候选） ----------
data_rows = [r for r in rows if r.has_data]
if data_rows:
    st.markdown("#### 📊 关键指标对比")
    long = []
    for r in data_rows:
        name = f"{r.school.name}·{r.major.name}"
        long.append({"候选": name, "指标": "录取概率", "数值": round(r.probability * 100)})
        long.append({"候选": name, "指标": "兴趣匹配", "数值": round(r.interest_match * 100)})
        long.append({"候选": name, "指标": "综合分", "数值": round(r.composite_score * 100)})
    fig = px.bar(pd.DataFrame(long), x="指标", y="数值", color="候选",
                 barmode="group", labels={"数值": "分值(0~100)"})
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

st.caption("说明：所有分数线/位次均为 " + f"{student.province}·{student.subject_type}"
           " 口径；综合分由录取概率、兴趣匹配及你的城市/层次/门类偏好加权得出。")
