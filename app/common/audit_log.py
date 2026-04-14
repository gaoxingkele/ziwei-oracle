"""Per-user daily JSONL audit log.

Writes one JSONL line per event to `logs/{user_id}/{YYYY-MM-DD}.jsonl`.
Retains at most `AUDIT_LOG_RETAIN_DAYS` (default 30) files per user.

Use `log_event(user_id, event, **fields)` directly, or let the context
helpers propagate user_id/trace_id across entry-point → engine → LLM.
"""
from __future__ import annotations

import contextvars
import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

LOG_ROOT = Path(os.getenv("AUDIT_LOG_ROOT", "logs"))
RETAIN_DAYS = int(os.getenv("AUDIT_LOG_RETAIN_DAYS", "30"))
ANON_USER = "anonymous"

_user_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("audit_user", default=ANON_USER)
_trace_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("audit_trace", default="")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_last_cleanup: dict[str, str] = {}


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def set_context(user_id: str | None = None, trace_id: str | None = None) -> tuple[contextvars.Token, contextvars.Token]:
    ut = _user_ctx.set(_sanitize(user_id) if user_id else _user_ctx.get())
    tt = _trace_ctx.set(trace_id or _trace_ctx.get() or new_trace_id())
    return ut, tt


def reset_context(tokens: tuple[contextvars.Token, contextvars.Token]) -> None:
    ut, tt = tokens
    try:
        _user_ctx.reset(ut)
    except ValueError:
        pass
    try:
        _trace_ctx.reset(tt)
    except ValueError:
        pass


def current_user_id() -> str:
    return _user_ctx.get() or ANON_USER


def current_trace_id() -> str:
    return _trace_ctx.get() or ""


def _sanitize(user_id: str | None) -> str:
    if not user_id:
        return ANON_USER
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(user_id))
    return safe[:64] or ANON_USER


def _lock_for(uid: str) -> threading.Lock:
    with _locks_guard:
        lk = _locks.get(uid)
        if lk is None:
            lk = threading.Lock()
            _locks[uid] = lk
        return lk


def _cleanup_old(user_dir: Path, uid: str, today: str) -> None:
    if _last_cleanup.get(uid) == today:
        return
    _last_cleanup[uid] = today
    cutoff = (datetime.now().date() - timedelta(days=RETAIN_DAYS - 1))
    for fp in user_dir.glob("*.jsonl"):
        try:
            d = datetime.strptime(fp.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            try:
                fp.unlink()
            except OSError:
                pass


def log_event(
    user_id: str | None,
    event: str,
    *,
    level: str = "INFO",
    trace_id: str | None = None,
    **fields: Any,
) -> None:
    """Append a single JSONL event. Never raises."""
    try:
        uid = _sanitize(user_id or current_user_id())
        tid = trace_id or current_trace_id()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        user_dir = LOG_ROOT / uid
        user_dir.mkdir(parents=True, exist_ok=True)
        fp = user_dir / f"{today}.jsonl"
        record = {
            "ts": now.isoformat(timespec="milliseconds"),
            "level": level,
            "event": event,
            "user_id": uid,
            "trace_id": tid,
        }
        for k, v in fields.items():
            record[k] = _coerce(v)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _lock_for(uid):
            with open(fp, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            _cleanup_old(user_dir, uid, today)
    except Exception:
        # logging must never break the app
        pass


def _coerce(v: Any) -> Any:
    """Keep values JSON-safe and bounded."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        if isinstance(v, str) and len(v) > 4000:
            return v[:4000] + f"...<truncated {len(v) - 4000} chars>"
        return v
    if isinstance(v, (list, tuple)):
        return [_coerce(x) for x in v][:50]
    if isinstance(v, dict):
        return {str(k): _coerce(x) for k, x in list(v.items())[:50]}
    return str(v)[:4000]
