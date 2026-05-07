from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType

TAG = __name__


class SystemTextMessageHandler(TextMessageHandler):
    """运行时更新 system prompt 的 addon 片段。

    协议：{"type": "system", "text": "<话题/上下文约束文本>"}

    行为：把 text 作为 addon 叠加到基线 system prompt 之后。基线首次使用时冻结
    为当前 conn.prompt（此时已经过 _init_prompt_enhancement 增强）。后续每次
    收到该消息都基于同一基线替换 addon，避免多次切话题累积。

    text 为空字符串时，清除 addon 回到基线。
    """

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.SYSTEM

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        addon = msg_json.get("text") or ""
        addon = addon.strip() if isinstance(addon, str) else ""

        if getattr(conn, "_system_prompt_base", None) is None:
            conn._system_prompt_base = conn.prompt or conn.config.get("prompt") or ""

        base = conn._system_prompt_base
        combined = (base + "\n\n" + addon) if (base and addon) else (addon or base)
        conn.change_system_prompt(combined)
        conn.logger.bind(tag=TAG).info(
            f"运行时更新 system addon: {addon[:80] if addon else '(cleared)'}"
        )
