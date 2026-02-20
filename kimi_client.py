# Kimi (Moonshot) API 客户端 - 配置从 .env 读取，支持多轮对话
from __future__ import annotations

from openai import OpenAI

from config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL


def get_client() -> OpenAI:
    if not KIMI_API_KEY:
        raise RuntimeError(
            "请在 .env 中设置 KIMI_API_KEY（或 MOONSHOT_API_KEY）。"
            "在 https://platform.moonshot.cn/console/api-keys 创建。"
        )
    return OpenAI(api_key=KIMI_API_KEY, base_url=KIMI_BASE_URL)


def chat(
    user_content: str,
    system_content: str | None = None,
    model: str | None = None,
) -> str:
    """单轮对话，返回助手回复文本。"""
    messages: list[dict[str, str]] = []
    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": user_content})
    content, _ = chat_with_messages(messages, model=model)
    return content


def chat_with_messages(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """
    多轮对话：传入完整 messages（含 system/user/assistant 历史），
    调用最新 API，返回 (本轮助手回复, 追加后的 messages)。
    """
    client = get_client()
    resp = client.chat.completions.create(
        model=model or KIMI_MODEL,
        messages=messages,
        temperature=0.3,
    )
    content = (resp.choices[0].message.content or "").strip()
    updated = list(messages)
    updated.append({"role": "assistant", "content": content})
    return content, updated
