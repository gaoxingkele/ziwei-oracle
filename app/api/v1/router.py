from fastapi import APIRouter
from app.api.v1.chart import router as chart_router
from app.api.v1.auth import router as auth_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(chart_router)
v1_router.include_router(auth_router)
