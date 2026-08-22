"""健康检查接口。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import engine, get_db

router = APIRouter(tags=["健康"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    components = {"mysql": "down", "redis": "down", "ai_service": "down"}
    try:
        db.execute(text("SELECT 1"))
        components["mysql"] = "up"
    except Exception:  # noqa: BLE001
        pass
    try:
        from redis import Redis
        from app.core.config import settings

        r = Redis.from_url(settings.redis_url, socket_timeout=2)
        components["redis"] = "up" if r.ping() else "down"
    except Exception:  # noqa: BLE001
        pass
    if getattr(__import__("app.core.config", fromlist=["settings"]).settings, "DEEPSEEK_API_KEY", ""):
        components["ai_service"] = "configured"
    status = "ok" if components["mysql"] == "up" else "degraded"
    return ok({"status": status, "components": components})
