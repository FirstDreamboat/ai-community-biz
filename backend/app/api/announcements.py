"""公告接口。"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ok
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.announcement import Announcement, ProjectProfile
from app.models.sys import SysUser
from app.services import audit_service, parse_service, scoring_service

router = APIRouter(prefix="/announcements", tags=["公告"])


class BatchParseBody(BaseModel):
    limit: int = 30
    reparse_failed: bool = False
    with_verify: bool = True


class ManualFixBody(BaseModel):
    """人工修正项目画像（仅接收可修正的业务字段）。"""
    purchaser: str | None = None
    project_type: str | None = None
    budget: Decimal | None = None
    bid_deadline: datetime | None = None
    open_time: datetime | None = None
    qualification: list | None = None
    tech_params: list | None = None
    household_cnt: int | None = None
    building_cnt: int | None = None
    area: Decimal | None = None
    contents: list | None = None
    fund_source: str | None = None
    stage: str | None = None
    relevance: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    address: str | None = None


def _ann_to_dict(a: Announcement) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "source_id": a.source_id,
        "source_url": a.source_url,
        "publish_time": a.publish_time,
        "crawl_time": a.crawl_time,
        "parse_status": a.parse_status,
        "verify_status": a.verify_status,
        "verify_result": a.verify_result,
        "parse_error": a.parse_error,
        "category": a.category,
    }


@router.get("")
def list_announcements(
    source_id: int | None = None,
    parse_status: int | None = None,
    verify_status: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    q = select(Announcement).where(Announcement.deleted == 0)
    if source_id:
        q = q.where(Announcement.source_id == source_id)
    if parse_status is not None:
        q = q.where(Announcement.parse_status == parse_status)
    if verify_status is not None:
        q = q.where(Announcement.verify_status == verify_status)
    if keyword:
        q = q.where(Announcement.title.like(f"%{keyword}%"))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    rows = db.execute(q.order_by(Announcement.id.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_ann_to_dict(a) for a in rows],
    })


@router.post("/batch-parse")
def batch_parse(
    body: BatchParseBody,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """后台批量解析未解析公告（解析 + AI二次核验，通过才生成商机）。"""
    state = parse_service.start_batch_parse(
        limit=body.limit, reparse_failed=body.reparse_failed, with_verify=body.with_verify
    )
    if state is None:
        raise HTTPException(status_code=409, detail="已有批量解析任务在运行")
    return ok(state)


@router.get("/batch-parse/status")
def batch_parse_status(
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    return ok(parse_service.get_batch_state())


@router.post("/batch-parse/trigger")
def trigger_batch_parse(
    body: BatchParseBody,
    x_internal_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """采集器内部触发批量解析（仅校验内部令牌，无需用户登录）。"""
    if not settings.INTERNAL_API_TOKEN or x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="内部触发令牌无效")
    state = parse_service.start_batch_parse(
        limit=body.limit, reparse_failed=body.reparse_failed, with_verify=body.with_verify
    )
    if state is None:
        return ok(parse_service.get_batch_state())
    return ok(state)


@router.get("/{ann_id}")
def get_announcement(
    ann_id: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    ann = db.execute(select(Announcement).where(Announcement.id == ann_id)).scalar_one_or_none()
    if ann is None:
        raise HTTPException(status_code=404, detail="公告不存在")
    profile = db.execute(
        select(ProjectProfile).where(ProjectProfile.announcement_id == ann_id)
    ).scalar_one_or_none()
    return ok({
        **_ann_to_dict(ann),
        "content": ann.content,
        "profile": profile,
    })


@router.post("/{ann_id}/re-parse")
async def re_parse(
    ann_id: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """单条重新解析（解析 + AI二次核验，通过才生成商机）。"""
    ann = db.execute(select(Announcement).where(Announcement.id == ann_id)).scalar_one_or_none()
    if ann is None:
        raise HTTPException(status_code=404, detail="公告不存在")

    try:
        res = await parse_service.parse_and_verify_one(db, ann, with_verify=True)
    except Exception as e:  # noqa: BLE001
        ann.parse_status = 2
        ann.parse_error = str(e)[:500]
        db.commit()
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")

    if res["error"]:
        raise HTTPException(status_code=500, detail=f"解析失败: {res['error']}")

    note = {
        1: "核验通过，已生成商机",
        2: "核验不通过，未生成商机",
        3: "待人工复核，未生成商机",
    }.get(res["verify_status"], "未知状态")
    return ok({
        "announcement_id": ann_id,
        "verify_status": res["verify_status"],
        "verify_note": note,
        "opportunity_id": res["opportunity_id"],
        "parsed_by": res["source"],
    })


@router.post("/{ann_id}/manual-fix")
def manual_fix(
    ann_id: int,
    body: ManualFixBody,
    db: Session = Depends(get_db),
    user: SysUser = Depends(get_current_user),
):
    """人工修正项目画像并重新生成商机（反馈闭环）。

    场景：AI 解析/核验不准时，人工确认字段后回写画像，
    触发重新评分生成商机，并将人工修正结果作为解析反馈。
    """
    ann = db.execute(select(Announcement).where(Announcement.id == ann_id)).scalar_one_or_none()
    if ann is None:
        raise HTTPException(status_code=404, detail="公告不存在")

    profile = db.execute(
        select(ProjectProfile).where(ProjectProfile.announcement_id == ann_id)
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="画像不存在，请先解析")

    fields = body.model_dump(exclude_none=True)
    for field, value in fields.items():
        setattr(profile, field, value)
    # 标记人工修正，反馈闭环（后续解析可学习）
    profile.human_verified = 1
    profile.parsed_by = "human"
    ann.parse_status = 1
    ann.verify_status = 1
    ann.verify_result = {
        **((ann.verify_result or {})),
        "manual_fixed": True,
        "fixed_by": user.username,
        "fixed_at": datetime.now().isoformat(timespec="seconds"),
        "fixed_fields": list(fields.keys()),
    }
    db.commit()

    # 人工确认后重新评分生成/更新商机（核验通过）
    try:
        opp = scoring_service.generate_opportunity(
            db, profile.id, verify_status=1,
            verify_note=f"人工修正确认（{user.username}）",
        )
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重新生成商机失败: {e}")

    audit_service.write_audit(
        db, user.id, "manual_fix", "project_profile", str(profile.id),
        {"announcement_id": ann_id, "fixed_fields": list(fields.keys())},
    )
    return ok({
        "announcement_id": ann_id,
        "profile_id": profile.id,
        "opportunity_id": opp.id,
        "total_score": float(opp.total_score),
        "level": opp.level,
        "fixed_fields": list(fields.keys()),
    })
