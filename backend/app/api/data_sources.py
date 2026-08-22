"""数据源管理接口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PERM_DATA_MANAGE, PERM_DATA_VIEW, ok, require_permission
from app.core.database import get_db
from app.models.data_source import DataSource
from app.models.sys import SysUser
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate
from app.services import audit_service, collector_service

router = APIRouter(prefix="/data-sources", tags=["数据源"])


@router.get("")
def list_data_sources(
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_DATA_VIEW)),
):
    rows = db.execute(
        select(DataSource).where(DataSource.deleted == 0).order_by(DataSource.id)
    ).scalars().all()
    return ok([_to_dict(d) for d in rows])


@router.post("")
def create_data_source(
    body: DataSourceCreate,
    user: SysUser = Depends(require_permission(PERM_DATA_MANAGE)),
    db: Session = Depends(get_db),
):
    ds = DataSource(**body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    audit_service.write_audit(db, user.id, "create", "data_source", str(ds.id))
    return ok(_to_dict(ds))


@router.put("/{ds_id}")
def update_data_source(
    ds_id: int,
    body: DataSourceUpdate,
    user: SysUser = Depends(require_permission(PERM_DATA_MANAGE)),
    db: Session = Depends(get_db),
):
    ds = _get_or_404(db, ds_id)
    for k, v in body.model_dump().items():
        setattr(ds, k, v)
    db.commit()
    db.refresh(ds)
    audit_service.write_audit(db, user.id, "update", "data_source", str(ds_id))
    return ok(_to_dict(ds))


@router.delete("/{ds_id}")
def delete_data_source(
    ds_id: int,
    user: SysUser = Depends(require_permission(PERM_DATA_MANAGE)),
    db: Session = Depends(get_db),
):
    ds = _get_or_404(db, ds_id)
    ds.deleted = 1
    db.commit()
    audit_service.write_audit(db, user.id, "delete", "data_source", str(ds_id))
    return ok()


@router.post("/{ds_id}/toggle")
def toggle_data_source(
    ds_id: int,
    user: SysUser = Depends(require_permission(PERM_DATA_MANAGE)),
    db: Session = Depends(get_db),
):
    ds = _get_or_404(db, ds_id)
    ds.status = 0 if ds.status == 1 else 1
    db.commit()
    db.refresh(ds)
    audit_service.write_audit(db, user.id, "toggle", "data_source", str(ds_id))
    return ok({"id": ds.id, "status": ds.status})


@router.post("/{ds_id}/run")
def run_data_source(
    ds_id: int,
    user: SysUser = Depends(require_permission(PERM_DATA_MANAGE)),
    db: Session = Depends(get_db),
):
    return ok(collector_service.trigger_collect(db, ds_id))


@router.get("/tasks")
def list_tasks(
    source_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_DATA_VIEW)),
):
    return ok(collector_service.list_tasks(db, source_id, status, page, page_size))


def _get_or_404(db: Session, ds_id: int) -> DataSource:
    ds = db.execute(
        select(DataSource).where(DataSource.id == ds_id, DataSource.deleted == 0)
    ).scalar_one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


def _to_dict(d: DataSource) -> dict:
    return {
        "id": d.id,
        "source_name": d.source_name,
        "source_type": d.source_type,
        "base_url": d.base_url,
        "list_pages": d.list_pages or [],
        "spider_class": d.spider_class,
        "keywords": d.keywords or [],
        "regions": d.regions or [],
        "schedule_cron": d.schedule_cron,
        "proxy_enabled": d.proxy_enabled,
        "status": d.status,
        "last_run_at": d.last_run_at,
        "last_run_status": d.last_run_status,
    }
