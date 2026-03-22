from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.common.exceptions import OracleError
from app.common.response import error, success

app = FastAPI(title="DS-Oracle API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(OracleError)
async def oracle_error_handler(request: Request, exc: OracleError):
    status = 400 if exc.code < 50000 else 500
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
