"""竞品监测接口。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.announcement import Announcement, ProjectProfile
from app.models.opportunity import CompetitorRecord
from app.models.sys import SysConfig, SysUser
from app.services import competitor_service

router = APIRouter(prefix="/competitors", tags=["竞品"])


class KeywordsBody(BaseModel):
    keywords: list[str] = []


class RecordBody(BaseModel):
    competitor: str
    province: str | None = None
    result: str = "中标"
    amount: float | None = None
    detected_at: datetime | None = None


@router.get("/records")
def list_records(
    competitor: str | None = None,
    province: str | None = None,
    result: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    q = select(CompetitorRecord)
    if competitor:
        q = q.where(CompetitorRecord.competitor == competitor)
    if province:
        q = q.where(CompetitorRecord.province == province)
    if result:
        q = q.where(CompetitorRecord.result == result)
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(CompetitorRecord.id.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    ann_ids = [c.announcement_id for c in rows if c.announcement_id]
    ann_map = {}
    if ann_ids:
        ann_map = {
            a.id: a.title
            for a in db.execute(
                select(Announcement).where(Announcement.id.in_(ann_ids))
            ).scalars()
        }
    items = [
        {"id": c.id, "competitor": c.competitor, "province": c.province,
         "result": c.result, "amount": c.amount, "detected_at": c.detected_at,
         "announcement_title": ann_map.get(c.announcement_id)}
        for c in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/analysis")
def analysis(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    by_region = db.execute(
        select(CompetitorRecord.competitor, CompetitorRecord.province, func.count(CompetitorRecord.id))
        .group_by(CompetitorRecord.competitor, CompetitorRecord.province)
        .order_by(func.count(CompetitorRecord.id).desc())
        .limit(30)
    ).all()
    by_product = db.execute(
        select(CompetitorRecord.competitor, ProjectProfile.project_type, func.count(CompetitorRecord.id))
        .join(ProjectProfile, ProjectProfile.id == CompetitorRecord.profile_id)
        .where(ProjectProfile.project_type.isnot(None), ProjectProfile.project_type != "")
        .group_by(CompetitorRecord.competitor, ProjectProfile.project_type)
        .order_by(func.count(CompetitorRecord.id).desc())
        .limit(30)
    ).all()
    return ok({
        "by_region": [{"competitor": r[0], "province": r[1], "count": r[2]} for r in by_region],
        "by_product": [{"competitor": r[0], "product": r[1], "count": r[2]} for r in by_product],
    })


@router.get("/keywords")
def get_keywords(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok({"keywords": competitor_service.get_keywords(db)})


@router.post("/keywords")
def save_keywords(
    body: KeywordsBody,
    db: Session = Depends(get_db),
    user: SysUser = Depends(get_current_user),
):
    """保存竞品监测关键词（去空、去重）。"""
    keywords = competitor_service.save_keywords(db, body.keywords, user_id=user.id)
    return ok({"keywords": keywords})


@router.post("/records")
def create_record(
    body: RecordBody,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """手动添加一条竞品记录。"""
    competitor = (body.competitor or "").strip()
    if not competitor:
        raise HTTPException(status_code=400, detail="竞品名称不能为空")
    rec = CompetitorRecord(
        competitor=competitor,
        province=body.province,
        result=body.result or "中标",
        amount=body.amount,
        detected_at=body.detected_at or datetime.now(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return ok({"id": rec.id})


@router.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """删除一条竞品记录。"""
    rec = db.execute(
        select(CompetitorRecord).where(CompetitorRecord.id == record_id)
    ).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    db.delete(rec)
    db.commit()
    return ok({"id": record_id})
