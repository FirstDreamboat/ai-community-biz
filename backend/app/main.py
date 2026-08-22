"""后端服务入口（FastAPI）。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("服务启动 %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    if settings.APP_ENV != "test":
        try:
            from app.tasks.scheduler import start_scheduler

            start_scheduler()
        except Exception as e:  # noqa: BLE001
            logger.warning("定时任务启动失败（不影响主服务）: %s", e)
    yield
    logger.info("服务关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI存量项目商机挖掘系统 API",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "docs": "/docs", "health": "/api/v1/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
