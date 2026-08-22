"""办事处/经销网点覆盖管理接口（区域覆盖匹配，对应 DBD 04_regions_offices.sql）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.office import Office
from app.models.sys import SysUser
from app.services import audit_service

router = APIRouter(prefix="/offices", tags=["办事处"])


class OfficeCreate(BaseModel):
    office_name: str = Field(min_length=1, max_length=100)
    office_type: str = Field(default="直属", pattern="^(直属|经销)$")
    province: str = Field(min_length=1, max_length=50)
    city: str | None = None
    cover_type: str = Field(default="cover", pattern="^(cover|radiate|none)$")
    address: str | None = None
    contact: str | None = None


def _to_dict(o: Office) -> dict:
    return {
        "id": o.id,
        "office_name": o.office_name,
        "office_type": o.office_type,
        "province": o.province,
        "city": o.city,
        "cover_type": o.cover_type,
        "address": o.address,
        "contact": o.contact,
        "status": o.status,
    }


@router.get("")
def list_offices(
    province: str | None = None,
    city: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    q = select(Office)
    if province:
        q = q.where(Office.province == province)
    if city:
        q = q.where(Office.city == city)
    if keyword:
        q = q.where(Office.office_name.like(f"%{keyword}%"))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.order_by(Office.id).offset((page - 1) * page_size)
                     .limit(page_size)).scalars().all()
    return ok({
        "total": total, "page": page, "page_size": page_size,
        "items": [_to_dict(o) for o in rows],
    })


@router.get("/match")
def match_office(
    province: str,
    city: str | None = None,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """区域覆盖匹配：优先省+市精确，降级到省匹配。"""
    def _pick(q):
        rows = db.execute(q.order_by(
            (Office.cover_type == "cover").desc(), Office.id
        )).scalars().all()
        return rows[0] if rows else None

    if city:
        office = _pick(select(Office).where(
            Office.province == province, Office.city == city, Office.status == 1
        ))
        if office is not None:
            return ok({**_to_dict(office), "match_level": "city"})
    office = _pick(select(Office).where(
        Office.province == province, Office.status == 1
    ))
    if office is not None:
        return ok({**_to_dict(office), "match_level": "province"})
    return ok(None)


@router.get("/coverage")
def coverage_summary(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """区域覆盖概览：按省份统计覆盖情况。"""
    rows = db.execute(
        select(Office.province, Office.cover_type, func.count(Office.id))
        .where(Office.status == 1)
        .group_by(Office.province, Office.cover_type)
    ).all()
    by_province: dict[str, dict] = {}
    for province, cover_type, cnt in rows:
        item = by_province.setdefault(province, {"province": province, "cover": 0, "radiate": 0})
        key = "cover" if cover_type == "cover" else "radiate"
        item[key] += int(cnt)
    items = sorted(by_province.values(), key=lambda x: x["province"])
    return ok({
        "total_provinces": len(items),
        "items": items,
    })


@router.post("")
def create_office(
    body: OfficeCreate,
    db: Session = Depends(get_db),
    user: SysUser = Depends(get_current_user),
):
    o = Office(**body.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    audit_service.write_audit(db, user.id, "create", "office", str(o.id), body.model_dump())
    return ok(_to_dict(o))


@router.put("/{office_id}")
def update_office(
    office_id: int,
    body: OfficeCreate,
    db: Session = Depends(get_db),
    user: SysUser = Depends(get_current_user),
):
    o = db.execute(select(Office).where(Office.id == office_id)).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="办事处不存在")
    for field, value in body.model_dump().items():
        setattr(o, field, value)
    db.commit()
    db.refresh(o)
    audit_service.write_audit(db, user.id, "update", "office", str(office_id))
    return ok(_to_dict(o))


@router.delete("/{office_id}")
def disable_office(
    office_id: int,
    db: Session = Depends(get_db),
    user: SysUser = Depends(get_current_user),
):
    o = db.execute(select(Office).where(Office.id == office_id)).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="办事处不存在")
    o.status = 0
    db.commit()
    audit_service.write_audit(db, user.id, "disable", "office", str(office_id))
    return ok()
