"""驾驶舱聚合数据服务。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement, ProjectProfile
from app.models.opportunity import Opportunity


def _score_bucket(score) -> str:
    s = float(score)
    if s >= 80:
        return "80-100"
    if s >= 60:
        return "60-79"
    if s >= 40:
        return "40-59"
    return "<40"


def overview(db: Session) -> dict:
    opps = db.execute(select(Opportunity).where(Opportunity.deleted == 0)).scalars().all()

    total = len(opps)
    high = sum(1 for o in opps if o.level == "high")
    following = sum(1 for o in opps if o.status in ("following", "bid"))
    won = sum(1 for o in opps if o.status == "won")

    # 区域分布（按画像省份聚合）
    region_rows = db.execute(
        select(ProjectProfile.province, func.count(ProjectProfile.id))
        .where(ProjectProfile.deleted == 0)
        .group_by(ProjectProfile.province)
        .order_by(func.count(ProjectProfile.id).desc())
        .limit(15)
    ).all()
    region_distribution = [
        {"province": p, "count": c} for p, c in region_rows if p
    ]

    # 评分分布
    buckets: dict[str, int] = {}
    for o in opps:
        b = _score_bucket(o.total_score)
        buckets[b] = buckets.get(b, 0) + 1
    score_distribution = [{"range": k, "count": v} for k, v in sorted(buckets.items(), reverse=True)]

    # 跟进漏斗
    status_count: dict[str, int] = {}
    for o in opps:
        status_count[o.status] = status_count.get(o.status, 0) + 1
    status_funnel = [{"status": k, "count": v} for k, v in status_count.items()]

    return {
        "total_opportunities": total,
        "high_level_count": high,
        "following_count": following,
        "won_count": won,
        "region_distribution": region_distribution,
        "score_distribution": score_distribution,
        "status_funnel": status_funnel,
    }


def trends(db: Session, type: str = "monthly",
           start_date: str | None = None, end_date: str | None = None) -> dict:
    """趋势分析：月度商机趋势 / 区域热度 / 产品需求排行。"""
    if type == "region_hot":
        rows = db.execute(
            select(ProjectProfile.province, func.count(Opportunity.id))
            .join(Opportunity, Opportunity.profile_id == ProjectProfile.id)
            .group_by(ProjectProfile.province)
            .order_by(func.count(Opportunity.id).desc())
            .limit(10)
        ).all()
        return {"type": type, "items": [{"region": r[0], "count": r[1]} for r in rows if r[0]]}

    if type == "product_demand":
        rows = db.execute(select(ProjectProfile.contents)).scalars().all()
        counter: dict[str, int] = {}
        for contents in rows:
            for tag in (contents or []):
                counter[tag] = counter.get(tag, 0) + 1
        items = sorted(
            [{"category": k, "count": v} for k, v in counter.items()],
            key=lambda x: x["count"], reverse=True,
        )
        return {"type": type, "items": items}

    # monthly：按公告发布时间月份聚合
    month_col = func.date_format(Announcement.publish_time, "%Y-%m").label("month")
    rows = db.execute(
        select(month_col, func.count(Opportunity.id))
        .join(ProjectProfile, ProjectProfile.id == Opportunity.profile_id)
        .join(Announcement, Announcement.id == ProjectProfile.announcement_id)
        .group_by(month_col)
        .order_by(month_col)
    ).all()
    return {"type": type, "items": [{"month": r[0], "count": r[1]} for r in rows]}


def heatmap(db: Session, level: str = "province", region: str | None = None) -> dict:
    col = {"province": ProjectProfile.province,
           "city": ProjectProfile.city,
           "district": ProjectProfile.district}.get(level, ProjectProfile.province)

    q = select(col, func.count(ProjectProfile.id)).where(ProjectProfile.deleted == 0).group_by(col)
    if region and level == "city":
        q = q.where(ProjectProfile.province == region)
    elif region and level == "district":
        q = q.where(ProjectProfile.city == region)

    rows = db.execute(q).all()
    items = [{"region": r or "未知", "count": c} for r, c in rows if r]
    return {"level": level, "items": items}
