"""AI 对话助手（DeepSeek，OpenAI 兼容接口）。

读取 DEEPSEEK_API_KEY（优先 streamlit secrets，其次环境变量）。未配置时
is_configured() 返回 False，调用方据此优雅降级，不影响其余功能。
擅长回答'某专业到底是干嘛的/学什么/将来干什么/适不适合我'，并解释推荐理由。
"""

from __future__ import annotations

import os

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

SYSTEM_PROMPT = (
    "你是'高考志愿小助手'，亲切、耐心、说人话。面向中国高考考生及家长，"
    "帮助他们看懂专业（是什么、学什么课、将来怎么就业、适合什么样的人）、"
    "理解志愿推荐的冲稳保逻辑并答疑。请基于提供的考生信息与推荐结果作答，"
    "不夸大、不承诺录取，提醒以官方招生章程为准。回答简洁、有条理。"
)


def _get_secret(name: str) -> str | None:
    try:
        import streamlit as st  # noqa: PLC0415

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name)


def is_configured() -> bool:
    return bool(_get_secret("DEEPSEEK_API_KEY"))


def _client():
    from openai import OpenAI  # noqa: PLC0415

    api_key = _get_secret("DEEPSEEK_API_KEY")
    base_url = _get_secret("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    return OpenAI(api_key=api_key, base_url=base_url)


def chat(messages: list[dict], context: str = "") -> str:
    """messages: [{'role':'user'/'assistant','content':...}]，context 为本轮背景信息。"""
    if not is_configured():
        return ("⚠️ 尚未配置 DeepSeek API Key，AI 助手暂不可用。\n\n"
                "请在 `.streamlit/secrets.toml` 中填入 `DEEPSEEK_API_KEY` 后重试"
                "（其余功能不受影响）。")
    model = _get_secret("DEEPSEEK_MODEL") or DEFAULT_MODEL
    system = SYSTEM_PROMPT + (f"\n\n【当前背景】\n{context}" if context else "")
    payload = [{"role": "system", "content": system}, *messages]
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=model, messages=payload, temperature=0.7, max_tokens=1200)
        return resp.choices[0].message.content or ""
    except Exception as e:  # 网络/额度等异常优雅降级
        return f"⚠️ AI 助手调用失败：{e}\n\n请稍后重试或检查网络与 API 配置。"
