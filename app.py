"""高考志愿填报推荐系统 — Streamlit 首页。

运行：  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 兼容未做 editable 安装的环境
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

from gaokao.data_loader import load_majors  # noqa: E402
from gaokao.recommender import trending  # noqa: E402
from gaokao.ui_helpers import ensure_data, get_student  # noqa: E402

st.set_page_config(page_title="高考志愿小助手", page_icon="🎓", layout="wide")

st.title("🎓 高考志愿小助手")
st.subheader("分数不浪费，专业不踩坑，志愿填得明明白白 ✨")

if not ensure_data():
    st.stop()

st.markdown(
    """
    欢迎！这是一个**有趣又靠谱**的高考志愿填报助手。它能帮你：

    - 🎯 **冲稳保志愿推荐**：用位次法 + 录取概率模型，给你一份合理梯度的志愿表
    - 🧭 **兴趣测评**：霍兰德职业兴趣小测验，找到"适合你"的专业方向
    - 📚 **专业百科**：把每个专业讲清楚——学什么、干什么、适合谁，不再两眼一抹黑
    - 🃏 **卡片选校**：像刷卡片一样轻松挑学校，喜欢的放进心愿单
    - 📊 **数据大屏**：位次走势、录取概率、兴趣雷达，一图看懂
    - 🤖 **AI 助手**：有问题随时问（由 DeepSeek 提供）
    """
)

student = get_student()
if student:
    st.success(f"已录入：{student.province} · {student.subject_type} · "
               f"分数 {student.score} · 位次 {student.rank}")
else:
    st.info("第一步：到 **📝 信息录入** 填写你的分数与位次，开启专属推荐。")

st.divider()

# 当下热门专业 Top 10
st.markdown("### 🔥 当下热门专业 Top 10")
st.caption("综合热度 = 专业热度 + 就业率 + 开设广度（点开 📚 专业百科 可看详情与个性化版）")

trends = trending.rank_hot_majors(load_majors(), top_n=10)
cols = st.columns(2)
for i, t in enumerate(trends):
    with cols[i % 2]:
        st.markdown(
            f"**{i + 1}. {t.name}**　`{t.category}`　🔥{t.score:.0f}　"
            f"就业 {t.avg_employment * 100:.0f}%　{t.count} 校开设")

st.divider()
st.caption("⚠️ 本系统当前使用模拟数据用于演示，推荐结果仅供参考，"
           "正式填报请以各省考试院与院校招生章程为准。")
