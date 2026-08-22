"""驾驶舱与报表接口。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import SysUser
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(dashboard_service.overview(db))


@router.get("/heatmap")
def heatmap(
    level: str = Query("province", pattern="^(province|city|district)$"),
    region: str | None = None,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(dashboard_service.heatmap(db, level, region))


@router.get("/trends")
def trends(
    type: str = Query("monthly", pattern="^(monthly|region_hot|product_demand)$"),
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    data = dashboard_service.trends(db, type, start_date, end_date) if hasattr(
        dashboard_service, "trends") else {"items": []}
    return ok(data)
