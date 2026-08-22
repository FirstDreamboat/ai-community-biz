"""智能商机挖掘接口（2026-08-22 新增）。"""
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import SysUser
from app.services import intel_service

router = APIRouter(prefix="/intel", tags=["智能商机挖掘"])


# ---------------- 请求模型 ----------------
class LegacyProjectIn(BaseModel):
    project_name: str
    community: str | None = None
    province: str | None = None
    city: str | None = None
    unit: str | None = None
    systems: list[str] | None = None
    device_brand: str | None = None
    install_year: int
    contract_end_year: int | None = None
    est_budget: float | None = None
    contact: str | None = None
    note: str | None = None
    status: int = 0


class UpdateOpportunityIn(BaseModel):
    status: str | None = None
    owner_name: str | None = None
    note: str | None = None


class StrategicCustomerIn(BaseModel):
    customer_name: str
    coop_type: str | None = None
    product_lines: list[str] | None = None
    contract_year: int | None = None
    contract_end_year: int
    annual_amount: float | None = None
    contact: str | None = None
    note: str | None = None


class SalesLeadIn(BaseModel):
    title: str
    customer_name: str | None = None
    province: str | None = None
    city: str | None = None
    budget: float | None = None
    stage: str | None = None
    channel: str | None = None
    reporter_name: str | None = None
    detail: str | None = None
    status: str = "new"
    owner_name: str | None = None
    follow_time: datetime | None = None


class CompetitorTrackIn(BaseModel):
    competitor: str
    community: str | None = None
    province: str | None = None
    city: str | None = None
    won_at: date | None = None
    track_type: str | None = None
    source_url: str | None = None
    status: str = "tracking"
    note: str | None = None


class AppealHotspotIn(BaseModel):
    community: str
    province: str | None = None
    city: str | None = None
    appeal_count: int = 0
    hot_score: int = 0
    topics: list[str] | None = None
    sample_titles: list[str] | None = None
    source_url: str | None = None
    period: str | None = None
    status: int = 0
    note: str | None = None


def _as_dict(body: BaseModel) -> dict[str, Any]:
    return body.model_dump(exclude_unset=True)


# ---------------- 存量项目 ----------------
@router.get("/legacy-projects")
def list_legacy(
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    status: int | None = None,
    window: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_legacy_projects(
        db, keyword, province, city, status, window, page, page_size))


@router.post("/legacy-projects")
def create_legacy(
    body: LegacyProjectIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.create_legacy_project(db, body.model_dump()))


@router.put("/legacy-projects/{pid}")
def update_legacy(
    pid: int,
    body: LegacyProjectIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_legacy_project(db, pid, body.model_dump()))


@router.delete("/legacy-projects/{pid}")
def delete_legacy(
    pid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_legacy_project(db, pid)
    return ok({"id": pid, "deleted": True})


# ---------------- 更新商机 ----------------
@router.get("/update-opportunities")
def list_update_opps(
    keyword: str | None = None,
    window_status: str | None = None,
    status: str | None = None,
    province: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_update_opportunities(
        db, keyword, window_status, status, province, page, page_size))


@router.post("/update-opportunities/generate")
def generate_update_opps(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """扫描存量台账，生成/刷新更新商机。"""
    return ok(intel_service.generate_update_opportunities(db))


@router.put("/update-opportunities/{oid}")
def update_update_opp(
    oid: int,
    body: UpdateOpportunityIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_update_opportunity(db, oid, _as_dict(body)))


@router.delete("/update-opportunities/{oid}")
def delete_update_opp(
    oid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_update_opportunity(db, oid)
    return ok({"id": oid, "deleted": True})


# ---------------- 战略客户集采 ----------------
@router.get("/strategic-customers")
def list_strategic(
    keyword: str | None = None,
    warning_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_strategic_customers(db, keyword, warning_only, page, page_size))


@router.post("/strategic-customers")
def create_strategic(
    body: StrategicCustomerIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.create_strategic_customer(db, body.model_dump()))


@router.put("/strategic-customers/{cid}")
def update_strategic(
    cid: int,
    body: StrategicCustomerIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_strategic_customer(db, cid, body.model_dump()))


@router.delete("/strategic-customers/{cid}")
def delete_strategic(
    cid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_strategic_customer(db, cid)
    return ok({"id": cid, "deleted": True})


# ---------------- 销售线索 ----------------
@router.get("/sales-leads")
def list_leads(
    keyword: str | None = None,
    status: str | None = None,
    province: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_sales_leads(db, keyword, status, province, page, page_size))


@router.post("/sales-leads")
def create_lead(
    body: SalesLeadIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.create_sales_lead(db, body.model_dump()))


@router.put("/sales-leads/{lid}")
def update_lead(
    lid: int,
    body: SalesLeadIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_sales_lead(db, lid, body.model_dump()))


@router.delete("/sales-leads/{lid}")
def delete_lead(
    lid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_sales_lead(db, lid)
    return ok({"id": lid, "deleted": True})


# ---------------- 竞品追踪 ----------------
@router.get("/competitor-tracks")
def list_tracks(
    keyword: str | None = None,
    competitor: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_competitor_tracks(db, keyword, competitor, status, page, page_size))


@router.post("/competitor-tracks")
def create_track(
    body: CompetitorTrackIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.create_competitor_track(db, body.model_dump()))


@router.post("/competitor-tracks/generate-from-records")
def generate_tracks(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """从竞品中标记录一键生成后续追踪。"""
    return ok(intel_service.generate_tracks_from_records(db))


@router.put("/competitor-tracks/{tid}")
def update_track(
    tid: int,
    body: CompetitorTrackIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_competitor_track(db, tid, body.model_dump()))


@router.delete("/competitor-tracks/{tid}")
def delete_track(
    tid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_competitor_track(db, tid)
    return ok({"id": tid, "deleted": True})


# ---------------- 诉求热点 ----------------
@router.get("/appeal-hotspots")
def list_hotspots(
    keyword: str | None = None,
    province: str | None = None,
    status: int | None = None,
    sort: str = "hot",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.list_appeal_hotspots(db, keyword, province, status, sort, page, page_size))


@router.post("/appeal-hotspots")
def create_hotspot(
    body: AppealHotspotIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.create_appeal_hotspot(db, body.model_dump()))


@router.put("/appeal-hotspots/{hid}")
def update_hotspot(
    hid: int,
    body: AppealHotspotIn,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(intel_service.update_appeal_hotspot(db, hid, body.model_dump()))


@router.delete("/appeal-hotspots/{hid}")
def delete_hotspot(
    hid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    intel_service.delete_appeal_hotspot(db, hid)
    return ok({"id": hid, "deleted": True})
