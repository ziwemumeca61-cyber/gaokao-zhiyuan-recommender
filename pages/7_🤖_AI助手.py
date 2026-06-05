"""AI 助手：由 DeepSeek 提供，答疑专业与志愿、解释推荐理由。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from gaokao import llm  # noqa: E402
from gaokao.data_loader import load_majors  # noqa: E402
from gaokao.models import TIERS  # noqa: E402
from gaokao.ui_helpers import ensure_data, get_student, get_wishlist  # noqa: E402

st.title("🤖 AI 志愿小助手")
st.caption("由 DeepSeek 提供。可以问：『计算机和软件工程有啥区别？』『金融适合我吗？』")

if not ensure_data():
    st.stop()

# ---------- DeepSeek API Key 配置（界面直接粘贴即可用） ----------
_configured = llm.is_configured()
with st.expander(
        "🔑 配置 DeepSeek API Key" + ("（已配置 ✅）" if _configured else "（必填，点这里展开）"),
        expanded=not _configured):
    st.caption("没有 key？去 platform.deepseek.com 注册并创建（按量付费，充几块钱即可）。"
               "粘贴的 key 只保存在你本次会话、不会上传或入库。")
    key = st.text_input("粘贴你的 DeepSeek API Key（sk- 开头）", type="password",
                        value=st.session_state.get("DEEPSEEK_API_KEY", ""),
                        placeholder="sk-...")
    if key.strip():
        st.session_state["DEEPSEEK_API_KEY"] = key.strip()
    if st.session_state.get("DEEPSEEK_API_KEY"):
        st.success("已填入，可以开始提问了。（想永久生效可写入 .streamlit/secrets.toml）")

if not llm.is_configured():
    st.info("👆 填入 DeepSeek API Key 后即可使用 AI 助手；其余功能不受影响。")
    st.stop()


def _build_context() -> str:
    parts: list[str] = []
    student = get_student()
    if student:
        parts.append(f"考生：{student.province}/{student.subject_type}，"
                     f"分数 {student.score}，位次 {student.rank}。")
        if student.has_assessment():
            top = sorted(student.riasec.items(), key=lambda x: x[1], reverse=True)[:2]
            parts.append("兴趣主导类型：" + "、".join(d for d, _ in top))
    buckets = st.session_state.get("recommendations")
    if buckets:
        for tier in TIERS:
            names = [f"{r.school.name}-{r.major.name}" for r in buckets[tier][:5]]
            if names:
                parts.append(f"{tier}档推荐：{'，'.join(names)}")
    wl = get_wishlist()
    if wl:
        majors = load_majors()
        liked = [majors[mid].name for mid in wl if mid in majors]
        if liked:
            parts.append("心愿单专业：" + "、".join(liked))
    return "\n".join(parts)


# 对话历史
history = st.session_state.setdefault("chat_history", [])
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 快捷提问
if not history:
    st.markdown("**试试这些问题：**")
    samples = ["我的推荐里冲稳保怎么搭配比较稳？",
               "计算机科学与技术和软件工程有什么区别？",
               "我的兴趣适合学什么专业？"]
    cols = st.columns(len(samples))
    for col, s in zip(cols, samples):
        if col.button(s, use_container_width=True):
            st.session_state["pending_prompt"] = s
            st.rerun()

prompt = st.chat_input("输入你的问题…") or st.session_state.pop("pending_prompt", None)

if prompt:
    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("思考中…"):
            answer = llm.chat(history, context=_build_context())
        st.markdown(answer)
    history.append({"role": "assistant", "content": answer})

if history and st.button("🧹 清空对话"):
    st.session_state["chat_history"] = []
    st.rerun()
