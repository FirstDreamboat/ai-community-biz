"""商机查询、跟进、分配服务。"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement, ProjectProfile
from app.models.opportunity import (
    CompetitorRecord,
    FollowUpLog,
    Opportunity,
)
from app.schemas.opportunity import (
    OpportunityDetail,
    OpportunityFilter,
    OpportunityListItem,
    ProjectProfileOut,
)

# 合法状态流转（对应 SRS BR 与状态机）
VALID_TRANSITIONS = {
    "new": {"following", "closed"},
    "following": {"bid", "closed"},
    "bid": {"won", "lost", "following"},
    "won": set(),
    "lost": {"closed"},
    "closed": set(),
}


def build_opportunity_query(db: Session, f: OpportunityFilter):
    q = (
        select(
            Opportunity,
            Announcement.title,
            Announcement.publish_time,
            Announcement.source_url,
            ProjectProfile.province,
            ProjectProfile.city,
            ProjectProfile.purchaser,
            ProjectProfile.budget,
            ProjectProfile.contents,
            ProjectProfile.stage,
        )
        .join(ProjectProfile, ProjectProfile.id == Opportunity.profile_id)
        .join(Announcement, Announcement.id == ProjectProfile.announcement_id)
        .where(Opportunity.deleted == 0)
    )

    if f.keyword:
        like = f"%{f.keyword}%"
        q = q.where(or_(Announcement.title.like(like), ProjectProfile.purchaser.like(like)))
    if f.province:
        q = q.where(ProjectProfile.province == f.province)
    if f.city:
        q = q.where(ProjectProfile.city == f.city)
    if f.level:
        q = q.where(Opportunity.level == f.level)
    if f.status:
        q = q.where(Opportunity.status == f.status)
    if f.min_score is not None:
        q = q.where(Opportunity.total_score >= f.min_score)
    if f.max_score is not None:
        q = q.where(Opportunity.total_score <= f.max_score)
    if f.relevance:
        q = q.where(ProjectProfile.relevance == f.relevance)
    if f.start_date:
        q = q.where(Announcement.publish_time >= datetime.combine(f.start_date, datetime.min.time()))
    if f.end_date:
        q = q.where(Announcement.publish_time <= datetime.combine(f.end_date, datetime.max.time()))

    sort_map = {
        "score_desc": Opportunity.total_score.desc(),
        "score_asc": Opportunity.total_score.asc(),
        "publish_time_desc": Announcement.publish_time.desc(),
        "publish_time_asc": Announcement.publish_time.asc(),
    }
    q = q.order_by(sort_map.get(f.sort, Opportunity.total_score.desc()))
    return q


def list_opportunities(db: Session, f: OpportunityFilter) -> dict:
    q = build_opportunity_query(db, f)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(
        q.offset((f.page - 1) * f.page_size).limit(f.page_size)
    ).all()

    items = [
        OpportunityListItem(
            id=o.id,
            title=title or "",
            province=province,
            city=city,
            purchaser=purchaser,
            budget=budget,
            contents=contents or [],
            stage=stage,
            total_score=o.total_score,
            level=o.level,
            status=o.status,
            publish_time=publish_time,
            source_url=source_url,
            verify_status=o.verify_status,
            verify_note=o.verify_note,
        )
        for o, title, publish_time, source_url, province, city, purchaser, budget, contents, stage in rows
    ]
    return {"total": total, "page": f.page, "page_size": f.page_size, "items": items}


def get_opportunity_detail(db: Session, opp_id: int) -> OpportunityDetail:
    opp = db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted == 0)
    ).scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="商机不存在")

    profile = db.execute(
        select(ProjectProfile).where(ProjectProfile.id == opp.profile_id)
    ).scalar_one_or_none()
    announcement = None
    if profile:
        announcement = db.execute(
            select(Announcement).where(Announcement.id == profile.announcement_id)
        ).scalar_one_or_none()

    follow_logs = db.execute(
        select(FollowUpLog)
        .where(FollowUpLog.opportunity_id == opp_id)
        .order_by(FollowUpLog.follow_time.desc())
    ).scalars().all()

    competitors = db.execute(
        select(CompetitorRecord).where(
            CompetitorRecord.profile_id == (profile.id if profile else -1)
        )
    ).scalars().all()

    item = OpportunityListItem(
        id=opp.id,
        title=announcement.title if announcement else "",
        province=profile.province if profile else None,
        city=profile.city if profile else None,
        purchaser=profile.purchaser if profile else None,
        budget=profile.budget if profile else None,
        contents=profile.contents or [] if profile else [],
        stage=profile.stage if profile else None,
        total_score=opp.total_score,
        level=opp.level,
        status=opp.status,
        publish_time=announcement.publish_time if announcement else None,
        source_url=announcement.source_url if announcement else None,
        verify_status=opp.verify_status,
        verify_note=opp.verify_note,
    )
    return OpportunityDetail(
        opportunity=item,
        profile=ProjectProfileOut.model_validate(profile) if profile else None,
        score_detail={
            "total": opp.total_score,
            "demand": opp.demand_score,
            "budget": opp.budget_score,
            "region": opp.region_score,
            "urgency": opp.urgency_score,
            "competition": opp.competition_score,
            "rules_version": opp.rules_version,
        },
        strategy=opp.follow_strategy,
        follow_logs=[{"id": l.id, "action": l.action, "note": l.note,
                      "next_plan": l.next_plan, "to_status": l.to_status,
                      "follow_time": l.follow_time.isoformat() if l.follow_time else None}
                     for l in follow_logs],
        competitors=[{"id": c.id, "competitor": c.competitor, "result": c.result,
                      "amount": c.amount} for c in competitors],
    )


def add_follow_up(
    db: Session, opp_id: int, user_id: int, action: str,
    to_status: str | None, note: str | None, next_plan: str | None,
    follow_time: datetime | None,
) -> FollowUpLog:
    opp = db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted == 0)
    ).scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="商机不存在")

    if to_status and to_status != opp.status:
        allowed = VALID_TRANSITIONS.get(opp.status, set())
        if to_status not in allowed:
            raise HTTPException(status_code=400, detail=f"非法状态流转: {opp.status} -> {to_status}")

    log = FollowUpLog(
        opportunity_id=opp_id,
        user_id=user_id,
        action=action,
        from_status=opp.status,
        to_status=to_status,
        note=note,
        next_plan=next_plan,
        follow_time=follow_time or datetime.now(),
    )
    if to_status:
        opp.status = to_status
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def assign_opportunity(db: Session, opp_id: int, owner_id: int) -> Opportunity:
    opp = db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted == 0)
    ).scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    opp.owner_id = owner_id
    opp.assign_time = datetime.now()
    db.commit()
    db.refresh(opp)
    return opp
