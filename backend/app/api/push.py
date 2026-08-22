"""推送记录管理接口（企微/钉钉/通用 webhook 真实下发）。"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PERM_OPP_FOLLOW, PERM_OPP_VIEW, ok, require_permission
from app.core.database import get_db
from app.models.opportunity import PushRecord
from app.models.sys import SysUser
from app.services import audit_service, push_service

router = APIRouter(prefix="/push", tags=["推送"])


class PushCreate(BaseModel):
    opportunity_id: int = Field(ge=1)
    push_channel: str = Field(pattern="^(wecom|dingtalk|webhook)$")
    receiver: str = Field(min_length=1, max_length=200)
    push_date: date | None = None
    auto_send: bool = True


class PushTest(BaseModel):
    push_channel: str = Field(pattern="^(wecom|dingtalk|webhook)$")
    content: str | None = None


@router.get("/records")
def list_push_records(
    opportunity_id: int | None = None,
    channel: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_OPP_VIEW)),
):
    q = select(PushRecord)
    if opportunity_id:
        q = q.where(PushRecord.opportunity_id == opportunity_id)
    if channel:
        q = q.where(PushRecord.push_channel == channel)
    if status:
        q = q.where(PushRecord.status == status)
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(PushRecord.id.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_to_dict(r) for r in rows],
    })


@router.post("/records")
def create_push_record(
    body: PushCreate,
    user: SysUser = Depends(require_permission(PERM_OPP_FOLLOW)),
    db: Session = Depends(get_db),
):
    try:
        record = push_service.create_push_record(
            db, body.opportunity_id, body.push_channel, body.receiver, body.push_date, body.auto_send
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    audit_service.write_audit(db, user.id, "create", "push_record", str(record.id))
    return ok(_to_dict(record))


@router.post("/records/{record_id}/send")
def send_record(
    record_id: int,
    user: SysUser = Depends(require_permission(PERM_OPP_FOLLOW)),
    db: Session = Depends(get_db),
):
    record = db.execute(select(PushRecord).where(PushRecord.id == record_id)).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="推送记录不存在")
    result = push_service.send_push_record(db, record)
    audit_service.write_audit(db, user.id, "send", "push_record", str(record_id))
    return ok({**_to_dict(record), "send_result": result})


@router.post("/records/send-pending")
def send_pending(
    channel: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: SysUser = Depends(require_permission(PERM_OPP_FOLLOW)),
    db: Session = Depends(get_db),
):
    result = push_service.send_pending_records(db, channel, limit)
    audit_service.write_audit(db, user.id, "send_pending", "push_record")
    return ok(result)


@router.post("/test")
def test_channel(
    body: PushTest,
    user: SysUser = Depends(require_permission(PERM_OPP_FOLLOW)),
):
    try:
        result = push_service.test_channel(body.push_channel, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error"))
    return ok(result)


def _to_dict(r: PushRecord) -> dict:
    return {
        "id": r.id,
        "opportunity_id": r.opportunity_id,
        "push_channel": r.push_channel,
        "receiver": r.receiver,
        "push_date": r.push_date,
        "content_snapshot": r.content_snapshot,
        "status": r.status,
        "error_msg": r.error_msg,
        "created_at": r.created_at,
    }
