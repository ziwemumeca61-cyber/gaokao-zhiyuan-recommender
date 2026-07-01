"""志愿体检：用大白话告诉考生——系统推荐怎么样、自己选的志愿靠不靠谱。

两个标签：
  ① 看系统推荐：体检系统自动给出的冲稳保推荐（梯度/把握/层次/下一步）。
  ② 诊断我选的志愿：体检你加进心愿单的志愿（保底够不够/选科符不符/有没有够不着）。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from gaokao.data_loader import load_admissions  # noqa: E402
from gaokao.diagnosis import diagnose  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.recommender import engine  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, render_scope_banner, require_student, wishlist_items,
)

st.title("📋 志愿体检")
st.caption("不堆图表，直接用大白话告诉你：系统推荐合不合理、你自己选的志愿靠不靠谱。")

if not ensure_data():
    st.stop()

student = require_student()
if student is None:
    st.stop()

render_scope_banner(student)

tab_rec, tab_diag = st.tabs(["📊 看系统推荐", "🩺 诊断我选的志愿"])


# ===========================================================================
# 标签一：体检系统自动推荐
# ===========================================================================
with tab_rec:
    buckets = engine.recommend(student, per_tier=10)
    flat = [r for t in TIERS for r in buckets[t]]
    if not flat:
        st.warning("暂时没匹配到合适的志愿，去 📝 信息录入 调整分数/位次或选考科目后再来。")
    else:
        n_chong, n_wen, n_bao = (len(buckets["冲"]), len(buckets["稳"]), len(buckets["保"]))

        # ---------- 1. 冲稳保梯度 ----------
        with st.container(border=True):
            st.markdown("### 1️⃣ 你的志愿梯度")
            st.markdown(
                f"系统给你找到：🔴 **冲 {n_chong} 个**、🟡 **稳 {n_wen} 个**、🟢 **保 {n_bao} 个**。")
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
                        "2. 回到本页 **🩺 诊断我选的志愿** 标签，看看自己这套靠不靠谱；\n"
                        "3. 到 **❤️ 我的志愿表** 把它们按「冲→稳→保」排好并一键导出。")
            c1, c2 = st.columns(2)
            c1.page_link("pages/3_🎯_志愿推荐.py", label="去看志愿推荐", icon="🎯")
            c2.page_link("pages/8_❤️_我的志愿表.py", label="去整理我的志愿表", icon="❤️")

        # ---------- 可选：历年位次走势 ----------
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
                fig.update_traces(line_color="#1FA463")
                fig.add_hline(y=student.rank, line_dash="dash", line_color="#00A699",
                              annotation_text=f"你的位次 {student.rank}")
                fig.update_xaxes(dtick=1)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("该专业暂无历年位次数据。")


# ===========================================================================
# 标签二：诊断考生自己选的志愿（心愿单）
# ===========================================================================
with tab_diag:
    st.caption("把你加进心愿单的意向志愿整体体检：梯度合不合理、保底够不够、有没有报不了或够不着的。")
    items = wishlist_items()
    if not items:
        st.info("心愿单还是空的～ 先去 **🎯 志愿推荐 / 🃏 卡片选校 / 🏛️ 院校查询** "
                "把意向专业加进来，再回来诊断。")
        st.page_link("pages/3_🎯_志愿推荐.py", label="➡️ 去志愿推荐", icon="🎯")
    else:
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

        st.markdown("#### 🩺 诊断与建议")
        _render = {"error": st.error, "warning": st.warning,
                   "info": st.info, "success": st.success}
        for severity, text in diag.findings:
            _render.get(severity, st.info)(text)

        st.page_link("pages/8_❤️_我的志愿表.py", label="➡️ 去『我的志愿表』排序并导出", icon="❤️")
        st.caption("诊断基于你省份科类的历年录取数据测算，仅供参考；正式填报以官方招生章程为准。")
