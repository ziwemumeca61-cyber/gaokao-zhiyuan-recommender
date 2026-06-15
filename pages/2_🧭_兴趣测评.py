"""兴趣测评：霍兰德 RIASEC 小测验，得出兴趣画像与适合的专业方向。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import assessment  # noqa: E402
from gaokao.data_loader import load_majors  # noqa: E402
from gaokao.ui_helpers import (  # noqa: E402
    ensure_data, get_student, render_major_detail, riasec_radar, set_student,
    wishlist_button,
)

st.title("🧭 霍兰德兴趣测评")
st.caption("18 句小描述，看哪句像你，凭第一感觉打分，没有对错——据此找到适合你的专业方向。")

if not ensure_data():
    st.stop()

st.markdown("**逐句打分**：每句独立选「像我 / 一般 / 不像我」，不用纠结、也不用跟别的比。")

_rating_labels = [lbl for lbl, _ in assessment.RATINGS]
_rating_value = dict(assessment.RATINGS)

with st.form("riasec_form"):
    answers: dict[int, float] = {}
    for idx, (text, _dim) in enumerate(assessment.STATEMENTS):
        st.markdown(f"**{idx + 1}. {text}**")
        pick = st.radio("（凭第一感觉选）", _rating_labels, index=None,
                        key=f"s{idx}", label_visibility="collapsed", horizontal=True)
        if pick is not None:
            answers[idx] = _rating_value[pick]
    submitted = st.form_submit_button("🎯 计算我的兴趣画像", type="primary")

if submitted and len(answers) < len(assessment.STATEMENTS):
    st.warning(f"还有 {len(assessment.STATEMENTS) - len(answers)} 句没打分，"
               "没打的不计入；打得越全结果越准。")

if submitted:
    riasec = assessment.score(answers)
    student = get_student()
    if student is not None:
        student.riasec = riasec
        set_student(student)
    st.session_state["riasec"] = riasec

riasec = st.session_state.get("riasec")
if riasec:
    st.divider()
    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(riasec_radar(riasec), use_container_width=True)
    with c2:
        st.markdown(f"#### 你的主导类型：{assessment.describe_types(riasec)}")
        cats = assessment.suggested_categories(riasec)
        st.markdown("**适合你的专业方向（门类）**：" + "、".join(cats))
        if get_student() is None:
            st.info("提示：填写 **📝 信息录入** 后，推荐会把你的兴趣一并考虑进来。")

    st.divider()
    st.markdown("### 🔎 这些方向都有哪些专业？（点开看科普）")
    majors = list(load_majors().values())
    shown: set[str] = set()
    for cat in assessment.suggested_categories(riasec):
        cat_majors = [m for m in majors if m.category == cat and m.name not in shown]
        cat_majors.sort(key=lambda m: m.name)
        for m in cat_majors[:3]:
            shown.add(m.name)
            with st.expander(f"{m.name}　`{cat}`"):
                render_major_detail(m)
                wishlist_button(m, key=f"wish_assess_{m.id}")
