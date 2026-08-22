"""API 路由汇总。"""
from fastapi import APIRouter

from app.api import (
    announcements,
    auth,
    competitors,
    dashboard,
    data_sources,
    follow_ups,
    health,
    intel,
    knowledge,
    offices,
    opportunities,
    push,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(opportunities.router)
api_router.include_router(dashboard.router)
api_router.include_router(announcements.router)
api_router.include_router(data_sources.router)
api_router.include_router(knowledge.router)
api_router.include_router(competitors.router)
api_router.include_router(follow_ups.router)
api_router.include_router(push.router)
api_router.include_router(offices.router)
api_router.include_router(users.router)
api_router.include_router(intel.router)
api_router.include_router(health.router)
