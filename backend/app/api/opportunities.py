"""商机接口。"""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PERM_OPP_ASSIGN, PERM_OPP_FOLLOW, ok, require_permission
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import SysUser
from app.schemas.opportunity import AssignRequest, FollowUpCreate, OpportunityFilter
from app.services import audit_service, opportunity_service, scoring_service

router = APIRouter(prefix="/opportunities", tags=["商机"])


@router.get("/export")
def export_opportunities(
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    level: str | None = None,
    status: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    relevance: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort: str = "score_desc",
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    """按当前筛选条件导出商机 CSV（UTF-8 BOM，Excel 可直接打开）。"""
    f = OpportunityFilter(
        keyword=keyword,
        province=province,
        city=city,
        level=level,
        status=status,
        min_score=min_score,
        max_score=max_score,
        relevance=relevance,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        sort=sort,
        page=1,
        page_size=10000,
    )
    result = opportunity_service.list_opportunities(db, f)
    rows = result["items"]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "标题", "省份", "城市", "采购方", "预算(万元)", "阶段", "评分", "级别", "状态", "发布时间", "来源链接"])
    for it in rows:
        writer.writerow([
            it.id,
            it.title,
            it.province or "",
            it.city or "",
            it.purchaser or "",
            it.budget,
            it.stage or "",
            it.total_score,
            it.level or "",
            it.status,
            it.publish_time.strftime("%Y-%m-%d") if it.publish_time else "",
            it.source_url or "",
        ])
    csv_data = "\ufeff" + buf.getvalue()
    filename = f"opportunities_{date.today().isoformat()}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("")
def list_opportunities(
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    level: str | None = None,
    status: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    relevance: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort: str = "score_desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    from datetime import date

    f = OpportunityFilter(
        keyword=keyword,
        province=province,
        city=city,
        level=level,
        status=status,
        min_score=min_score,
        max_score=max_score,
        relevance=relevance,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ok(opportunity_service.list_opportunities(db, f))


@router.get("/{opp_id}")
def get_opportunity(
    opp_id: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(get_current_user),
):
    detail = opportunity_service.get_opportunity_detail(db, opp_id)
    return ok(detail.model_dump())


@router.post("/{opp_id}/recalc")
def recalc_opportunity(
    opp_id: int,
    user: SysUser = Depends(require_permission(PERM_OPP_FOLLOW)),
    db: Session = Depends(get_db),
):
    """按最新评分规则与数据（权重/办事处/知识库/竞品）重新计算商机评分。"""
    from app.models.opportunity import Opportunity

    opp = db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted == 0)
    ).scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    if not opp.profile_id:
        raise HTTPException(status_code=400, detail="商机缺少项目画像，无法重算")
    opp = scoring_service.generate_opportunity(db, opp.profile_id)
    audit_service.write_audit(db, user.id, "recalc", "opportunity", str(opp_id),
                              {"total_score": str(opp.total_score)})
    return ok({"opportunity_id": opp.id, "total_score": opp.total_score, "level": opp.level})


@router.post("/{opp_id}/follow-up")
def add_follow_up(
    opp_id: int,
    body: FollowUpCreate,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = opportunity_service.add_follow_up(
        db, opp_id, user.id, body.action, body.to_status,
        body.note, body.next_plan, body.follow_time,
    )
    return ok({"id": log.id, "to_status": log.to_status})


@router.post("/{opp_id}/assign")
def assign_opportunity(
    opp_id: int,
    body: AssignRequest,
    user: SysUser = Depends(require_permission(PERM_OPP_ASSIGN)),
    db: Session = Depends(get_db),
):
    opp = opportunity_service.assign_opportunity(db, opp_id, body.owner_id)
    audit_service.write_audit(db, user.id, "assign", "opportunity", str(opp_id),
                              {"owner_id": body.owner_id})
    return ok({"opportunity_id": opp.id, "owner_id": opp.owner_id})
