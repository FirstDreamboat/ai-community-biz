"""跟进记录接口。"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.announcement import Announcement, ProjectProfile
from app.models.opportunity import FollowUpLog, Opportunity
from app.models.sys import SysUser

router = APIRouter(prefix="/follow-ups", tags=["跟进"])


@router.get("")
def list_follow_ups(
    opportunity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    q = select(FollowUpLog)
    if opportunity_id:
        q = q.where(FollowUpLog.opportunity_id == opportunity_id)
    if user_id:
        q = q.where(FollowUpLog.user_id == user_id)
    if action:
        q = q.where(FollowUpLog.action == action)
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(FollowUpLog.follow_time.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = [
        {"id": l.id, "opportunity_id": l.opportunity_id, "user_id": l.user_id,
         "action": l.action, "from_status": l.from_status, "to_status": l.to_status,
         "note": l.note, "next_plan": l.next_plan, "follow_time": l.follow_time}
        for l in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/overdue")
def list_overdue(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """超过24小时未首次跟进的高评分商机。"""
    threshold = datetime.now() - timedelta(hours=24)
    q = (
        select(Opportunity, Announcement.title, ProjectProfile.province)
        .join(ProjectProfile, ProjectProfile.id == Opportunity.profile_id)
        .join(Announcement, Announcement.id == ProjectProfile.announcement_id)
        .where(
            Opportunity.level == "high",
            Opportunity.status.in_(["new", "following"]),
            Opportunity.created_at < threshold,
        )
    )
    rows = db.execute(q.limit(50)).all()
    items = [{"id": o.id, "title": t, "province": p, "score": o.total_score,
              "status": o.status, "created_at": o.created_at} for o, t, p in rows]
    return ok({"items": items})
