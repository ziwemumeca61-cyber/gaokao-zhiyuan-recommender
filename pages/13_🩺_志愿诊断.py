"""志愿诊断：把你的意向志愿（心愿单）整体体检，给出合理化建议。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao.diagnosis import diagnose  # noqa: E402
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

diag = diagnose(student, items)

rows = [{
    "院校·专业": it.name,
    "状态": it.status,
    "冲稳保": it.tier,
    "录取概率": f"{it.prob * 100:.0f}%" if it.has_data else "—",
    "参考位次": it.ref_rank if it.has_data else "—",
    "选科要求": it.req_label,
} for it in diag.items]

st.markdown(f"#### 你的意向志愿（共 {diag.count} 个）")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------- 诊断结论 ----------
st.markdown("#### 🩺 诊断与建议")
_render = {"error": st.error, "warning": st.warning, "info": st.info, "success": st.success}
for severity, text in diag.findings:
    _render.get(severity, st.info)(text)

st.page_link("pages/8_❤️_我的志愿表.py", label="➡️ 去『我的志愿表』排序并导出", icon="❤️")
st.caption("诊断基于你省份科类的历年录取数据测算，仅供参考；正式填报以官方招生章程为准。")
