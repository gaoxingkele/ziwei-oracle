import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.common.exceptions import OracleError
from app.common.response import error, success
from app.common import audit_log

app = FastAPI(title="DS-Oracle API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_user_id(request: Request) -> str:
    """Best-effort: JWT sub > API token suffix > device_id header > anonymous."""
    auth = request.headers.get("authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.query_params.get("token", "")
    if token:
        try:
            from app.auth.jwt import decode_token
            claims = decode_token(token)
            sub = claims.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
        return f"token_{token[-8:]}"
    dev = request.headers.get("x-device-id") or request.headers.get("x-user-id")
    if dev:
        return str(dev)
    return audit_log.ANON_USER


@app.middleware("http")
async def audit_mw(request: Request, call_next):
    trace_id = audit_log.new_trace_id()
    user_id = _extract_user_id(request)
    tokens = audit_log.set_context(user_id=user_id, trace_id=trace_id)
    request.state.trace_id = trace_id
    start = time.perf_counter()
    client_host = request.client.host if request.client else None
    try:
        query = dict(request.query_params)
        if "token" in query:
            query["token"] = "***"
    except Exception:
        query = {}
    audit_log.log_event(
        user_id, "request_in",
        trace_id=trace_id,
        method=request.method,
        path=str(request.url.path),
        query=query,
        client=client_host,
        ua=request.headers.get("user-agent"),
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        audit_log.log_event(
            user_id, "request_error", level="ERROR", trace_id=trace_id,
            error_type=type(exc).__name__, error=str(exc),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
        audit_log.reset_context(tokens)
        raise
    audit_log.log_event(
        user_id, "response_out", trace_id=trace_id,
        status=response.status_code,
        duration_ms=int((time.perf_counter() - start) * 1000),
    )
    audit_log.reset_context(tokens)
    return response


@app.exception_handler(OracleError)
async def oracle_error_handler(request: Request, exc: OracleError):
    status = 400 if exc.code < 50000 else 500
    audit_log.log_event(
        audit_log.current_user_id(), "oracle_error", level="WARNING",
        code=exc.code, message=exc.message, path=str(request.url.path),
    )
    return JSONResponse(status_code=status, content=error(exc.code, exc.message))

@app.get("/api/v1/health")
async def health():
    return success({"status": "ok"})

from app.api.v1.router import v1_router
app.include_router(v1_router)

# Register engines
import importlib
importlib.import_module("app.engine.ziwei")
importlib.import_module("app.engine.meihua")
importlib.import_module("app.engine.liuyao")
importlib.import_module("app.engine.astrology")
importlib.import_module("app.engine.bazi")
importlib.import_module("app.engine.qimen")
importlib.import_module("app.engine.liuren")
importlib.import_module("app.engine.iching")
importlib.import_module("app.engine.qianwen")
importlib.import_module("app.engine.jiemeng")
importlib.import_module("app.engine.name_analysis")
importlib.import_module("app.engine.hehun")
importlib.import_module("app.engine.jiri")
