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
st.caption("24 道小题，了解你是哪种'职业兴趣类型'，从'你是什么样的人'找到'适合的专业'。")

if not ensure_data():
    st.stop()

st.markdown("请根据自己的真实想法，对每句话的认同程度打分（1=很不符合，5=很符合）。")

with st.form("riasec_form"):
    answers: dict[int, int] = {}
    for idx, (text, _dim) in enumerate(assessment.QUESTIONS):
        answers[idx] = st.slider(f"{idx + 1}. {text}", 1, 5, 3, key=f"q{idx}")
    submitted = st.form_submit_button("🎯 计算我的兴趣画像", type="primary")

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
        # 每个门类挑热度最高的几个去重展示
        cat_majors.sort(key=lambda m: m.heat, reverse=True)
        for m in cat_majors[:3]:
            shown.add(m.name)
            with st.expander(f"{m.name}　`{cat}`　🔥{m.heat:.0f}"):
                render_major_detail(m)
                wishlist_button(m, key=f"wish_assess_{m.id}")
