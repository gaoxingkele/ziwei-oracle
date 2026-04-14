# Kimi (Moonshot) API 客户端 - 配置从 .env 读取，支持多轮对话
from __future__ import annotations

import time

from openai import OpenAI

from config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

try:
    from app.common import audit_log
except Exception:  # app package may not be importable in minimal contexts
    audit_log = None  # type: ignore


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
    use_model = model or KIMI_MODEL
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    if audit_log is not None:
        audit_log.log_event(
            None, "llm_request",
            provider="kimi", model=use_model,
            messages_count=len(messages),
            user_preview=last_user[:500],
        )
    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=use_model,
            messages=messages,
            temperature=0.3,
        )
    except Exception as exc:
        if audit_log is not None:
            audit_log.log_event(
                None, "llm_error", level="ERROR",
                provider="kimi", model=use_model,
                error_type=type(exc).__name__, error=str(exc),
                duration_ms=int((time.perf_counter() - start) * 1000),
            )
        raise
    content = (resp.choices[0].message.content or "").strip()
    if audit_log is not None:
        usage = getattr(resp, "usage", None)
        audit_log.log_event(
            None, "llm_response",
            provider="kimi", model=use_model,
            content_len=len(content),
            content_preview=content[:500],
            prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
            total_tokens=getattr(usage, "total_tokens", None) if usage else None,
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
    updated = list(messages)
    updated.append({"role": "assistant", "content": content})
    return content, updated
