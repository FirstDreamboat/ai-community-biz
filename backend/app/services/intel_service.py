"""智能商机挖掘服务（2026-08-22 新增）。

覆盖：
- 存量项目台账 + 设备更新窗口推算（更新商机）
- 战略客户集采台账 + 到期预警
- 销售线索本地评分入池
- 竞品中标后续追踪
- 12345 诉求热点聚合
"""
import re
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement, ProjectProfile
from app.models.intel import (
    AppealHotspot,
    CompetitorTrack,
    LegacyProject,
    SalesLead,
    StrategicCustomer,
    UpdateOpportunity,
)
from app.models.opportunity import CompetitorRecord
from app.services.verify_service import INDUSTRY_KEYWORDS

CURRENT_YEAR = datetime.now().year


def _page(items: list, total: int) -> dict:
    return {"list": items, "total": total}


def _window_of(age: int) -> tuple[str, str] | None:
    """按设备年限推算更新窗口：(状态, 推荐动作)。"""
    if age < 6:
        return None
    if age <= 8:
        return "imminent", "设备进入临期(6-8年)，建议提前介入，输出换新方案建议书，抢占方案设计话语权"
    if age <= 10:
        return "due", "进入换新窗口期(8-10年)，立即对接业主/物业，推荐IP两线免布线改造方案，安排样机演示"
    return "overdue", "设备超期(>10年)，故障频发，以'安全+节能'为切入点推动整体更换，发起专项沟通"


# ============================================================
# 一、存量项目台账
# ============================================================
def list_legacy_projects(db: Session, keyword=None, province=None, city=None,
                         status=None, window=None, page=1, page_size=20) -> dict:
    q = select(LegacyProject).where(LegacyProject.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(LegacyProject.project_name.like(like), LegacyProject.community.like(like),
                        LegacyProject.unit.like(like)))
    if province:
        q = q.where(LegacyProject.province == province)
    if city:
        q = q.where(LegacyProject.city == city)
    if status is not None:
        q = q.where(LegacyProject.status == status)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = db.execute(
        q.order_by(LegacyProject.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = []
    for p in rows:
        age = CURRENT_YEAR - p.install_year
        w = _window_of(age)
        items.append({
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            "age_years": age,
            "window_status": w[0] if w else "normal",
            "window_action": w[1] if w else "设备仍在服役期，持续维护客户关系",
        })
    return _page(items, total)


def create_legacy_project(db: Session, data: dict) -> dict:
    p = LegacyProject(**data)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {c.name: getattr(p, c.name) for c in p.__table__.columns}


def update_legacy_project(db: Session, pid: int, data: dict) -> dict:
    p = db.get(LegacyProject, pid)
    if not p or p.deleted:
        raise ValueError("存量项目不存在")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return {c.name: getattr(p, c.name) for c in p.__table__.columns}


def delete_legacy_project(db: Session, pid: int) -> None:
    p = db.get(LegacyProject, pid)
    if p:
        p.deleted = 1
        db.commit()


# ============================================================
# 二、更新商机（由存量台账推算）
# ============================================================
def list_update_opportunities(db: Session, keyword=None, window_status=None,
                              status=None, province=None, page=1, page_size=20) -> dict:
    q = select(UpdateOpportunity).where(UpdateOpportunity.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(UpdateOpportunity.community.like(like), UpdateOpportunity.recommend_action.like(like)))
    if window_status:
        q = q.where(UpdateOpportunity.window_status == window_status)
    if status:
        q = q.where(UpdateOpportunity.status == status)
    if province:
        q = q.where(UpdateOpportunity.province == province)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = db.execute(
        q.order_by(UpdateOpportunity.window_status.desc(), UpdateOpportunity.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [{c.name: getattr(o, c.name) for c in o.__table__.columns} for o in rows]
    return _page(items, total)


def generate_update_opportunities(db: Session, current_year: int | None = None) -> dict:
    """扫描在用存量项目，生成/刷新更新商机（幂等）。"""
    cy = current_year or CURRENT_YEAR
    projects = db.execute(
        select(LegacyProject).where(LegacyProject.deleted == 0, LegacyProject.status == 0)
    ).scalars().all()
    created = updated = skipped = 0
    for p in projects:
        age = cy - p.install_year
        w = _window_of(age)
        if not w:
            skipped += 1
            continue
        wstatus, action = w
        existing = db.execute(
            select(UpdateOpportunity).where(
                UpdateOpportunity.legacy_project_id == p.id, UpdateOpportunity.deleted == 0
            )
        ).scalars().first()
        payload = dict(
            legacy_project_id=p.id, community=p.community, province=p.province, city=p.city,
            age_years=age, window_status=wstatus, recommend_action=action,
            est_budget=p.est_budget,
        )
        if existing:
            existing.age_years = age
            existing.window_status = wstatus
            existing.recommend_action = action
            existing.est_budget = p.est_budget
            updated += 1
        else:
            db.add(UpdateOpportunity(**payload))
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def update_update_opportunity(db: Session, oid: int, data: dict) -> dict:
    o = db.get(UpdateOpportunity, oid)
    if not o or o.deleted:
        raise ValueError("更新商机不存在")
    for k, v in data.items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


def delete_update_opportunity(db: Session, oid: int) -> None:
    o = db.get(UpdateOpportunity, oid)
    if o:
        o.deleted = 1
        db.commit()


# ============================================================
# 三、战略客户集采台账
# ============================================================
def _customer_status(end_year: int) -> int:
    """0正常 1预警(距到期<=1年或已到期未流失) 2流失(到期>1年仍无动作)。"""
    if end_year < CURRENT_YEAR - 1:
        return 2
    if end_year <= CURRENT_YEAR + 1:
        return 1
    return 0


def list_strategic_customers(db: Session, keyword=None, warning_only=False, page=1, page_size=20) -> dict:
    q = select(StrategicCustomer).where(StrategicCustomer.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(StrategicCustomer.customer_name.like(like), StrategicCustomer.coop_type.like(like)))
    if warning_only:
        q = q.where(or_(
            StrategicCustomer.contract_end_year <= CURRENT_YEAR + 1,
            StrategicCustomer.status == 1,
        ))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = db.execute(
        q.order_by(StrategicCustomer.contract_end_year.asc(), StrategicCustomer.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = []
    for c in rows:
        d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        d["warning_level"] = _customer_status(c.contract_end_year)
        d["months_left"] = (c.contract_end_year - CURRENT_YEAR) * 12
        items.append(d)
    return _page(items, total)


def create_strategic_customer(db: Session, data: dict) -> dict:
    c = StrategicCustomer(**data)
    c.status = _customer_status(c.contract_end_year)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {col.name: getattr(c, col.name) for col in c.__table__.columns}


def update_strategic_customer(db: Session, cid: int, data: dict) -> dict:
    c = db.get(StrategicCustomer, cid)
    if not c or c.deleted:
        raise ValueError("战略客户不存在")
    for k, v in data.items():
        setattr(c, k, v)
    c.status = _customer_status(c.contract_end_year)
    db.commit()
    db.refresh(c)
    return {col.name: getattr(c, col.name) for col in c.__table__.columns}


def delete_strategic_customer(db: Session, cid: int) -> None:
    c = db.get(StrategicCustomer, cid)
    if c:
        c.deleted = 1
        db.commit()


# ============================================================
# 四、销售线索（本地评分）
# ============================================================
_STAGE_WEIGHT = {"初步接触": 0, "需求确认": 15, "方案报价": 25, "投标": 35, "合同谈判": 45}
_CHANNEL_WEIGHT = {"老客户转介绍": 10, "销售报备": 8, "展会": 6, "行业活动": 6, "电话营销": 3, "其他": 2}


def _score_lead(data: dict) -> int:
    text = f"{data.get('title', '')} {data.get('detail', '')} {data.get('customer_name', '')}"
    hits = [k for k in INDUSTRY_KEYWORDS if k in text]
    industry = min(len(hits) * 8, 40)
    stage = _STAGE_WEIGHT.get(data.get("stage") or "", 0)
    channel = _CHANNEL_WEIGHT.get(data.get("channel") or "", 2)
    budget = data.get("budget") or 0
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        budget = 0
    if budget <= 0:
        budget_s = 0
    elif budget <= 50:
        budget_s = 5
    elif budget <= 200:
        budget_s = 10
    elif budget <= 500:
        budget_s = 15
    else:
        budget_s = 20
    return min(100, 20 + industry + stage + channel + budget_s)


def list_sales_leads(db: Session, keyword=None, status=None, province=None, page=1, page_size=20) -> dict:
    q = select(SalesLead).where(SalesLead.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(SalesLead.title.like(like), SalesLead.customer_name.like(like),
                        SalesLead.detail.like(like)))
    if status:
        q = q.where(SalesLead.status == status)
    if province:
        q = q.where(SalesLead.province == province)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = db.execute(
        q.order_by(SalesLead.score.desc(), SalesLead.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [{c.name: getattr(s, c.name) for c in s.__table__.columns} for s in rows]
    return _page(items, total)


def create_sales_lead(db: Session, data: dict) -> dict:
    s = SalesLead(**data)
    s.score = _score_lead(data)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {c.name: getattr(s, c.name) for c in s.__table__.columns}


def update_sales_lead(db: Session, lid: int, data: dict) -> dict:
    s = db.get(SalesLead, lid)
    if not s or s.deleted:
        raise ValueError("销售线索不存在")
    for k, v in data.items():
        setattr(s, k, v)
    s.score = _score_lead(data)
    db.commit()
    db.refresh(s)
    return {c.name: getattr(s, c.name) for c in s.__table__.columns}


def delete_sales_lead(db: Session, lid: int) -> None:
    s = db.get(SalesLead, lid)
    if s:
        s.deleted = 1
        db.commit()


# ============================================================
# 五、竞品中标后续追踪
# ============================================================
def _extract_community(text: str) -> str | None:
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9·]{2,20}?(?:小区|社区|园区|大厦|医院|学校|广场|街道|安置房))", text or "")
    return m.group(1) if m else None


def list_competitor_tracks(db: Session, keyword=None, competitor=None, status=None, page=1, page_size=20) -> dict:
    q = select(CompetitorTrack).where(CompetitorTrack.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(CompetitorTrack.community.like(like), CompetitorTrack.note.like(like)))
    if competitor:
        q = q.where(CompetitorTrack.competitor == competitor)
    if status:
        q = q.where(CompetitorTrack.status == status)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = db.execute(
        q.order_by(CompetitorTrack.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [{c.name: getattr(t, c.name) for c in t.__table__.columns} for t in rows]
    return _page(items, total)


def create_competitor_track(db: Session, data: dict) -> dict:
    t = CompetitorTrack(**data)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {c.name: getattr(t, c.name) for c in t.__table__.columns}


def update_competitor_track(db: Session, tid: int, data: dict) -> dict:
    t = db.get(CompetitorTrack, tid)
    if not t or t.deleted:
        raise ValueError("竞品追踪不存在")
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return {c.name: getattr(t, c.name) for c in t.__table__.columns}


def delete_competitor_track(db: Session, tid: int) -> None:
    t = db.get(CompetitorTrack, tid)
    if t:
        t.deleted = 1
        db.commit()


def generate_tracks_from_records(db: Session) -> dict:
    """从竞品中标记录（competitor_record）一键生成后续追踪。"""
    records = db.execute(
        select(CompetitorRecord).where(
            CompetitorRecord.result.in_(["中标", "win"]),
        )
    ).scalars().all()
    created = existed = 0
    for r in records:
        existed_row = db.execute(
            select(CompetitorTrack).where(
                CompetitorTrack.competitor == r.competitor,
                CompetitorTrack.community.is_(None),
                CompetitorTrack.created_at >= r.detected_at,
            )
        ).scalars().first()
        # 简化去重：同一竞品同一省份同一时期只生成一条
        dup = db.execute(
            select(CompetitorTrack).where(
                CompetitorTrack.competitor == r.competitor,
                CompetitorTrack.province == r.province,
                CompetitorTrack.deleted == 0,
            )
        ).scalars().first()
        if dup:
            existed += 1
            continue
        ann = None
        if r.announcement_id:
            ann = db.get(Announcement, r.announcement_id)
        title = ann.title if ann else ""
        community = _extract_community(title)
        db.add(CompetitorTrack(
            competitor=r.competitor,
            community=community,
            province=r.province,
            won_at=r.detected_at.date() if isinstance(r.detected_at, datetime) else r.detected_at,
            track_type="后续标段",
            source_url=ann.source_url if ann else None,
            note=f"由竞品中标记录自动生成：{title or '无标题'}，中标金额{r.amount if r.amount else '未知'}万元",
        ))
        created += 1
    db.commit()
    return {"created": created, "existed": existed}


# ============================================================
# 六、12345 诉求热点
# ============================================================
def list_appeal_hotspots(db: Session, keyword=None, province=None, status=None, sort="hot", page=1, page_size=20) -> dict:
    q = select(AppealHotspot).where(AppealHotspot.deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(AppealHotspot.community.like(like), AppealHotspot.note.like(like)))
    if province:
        q = q.where(AppealHotspot.province == province)
    if status is not None:
        q = q.where(AppealHotspot.status == status)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    order = AppealHotspot.hot_score.desc() if sort == "hot" else AppealHotspot.appeal_count.desc()
    rows = db.execute(
        q.order_by(order, AppealHotspot.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [{c.name: getattr(h, c.name) for c in h.__table__.columns} for h in rows]
    return _page(items, total)


def create_appeal_hotspot(db: Session, data: dict) -> dict:
    h = AppealHotspot(**data)
    db.add(h)
    db.commit()
    db.refresh(h)
    return {c.name: getattr(h, c.name) for c in h.__table__.columns}


def update_appeal_hotspot(db: Session, hid: int, data: dict) -> dict:
    h = db.get(AppealHotspot, hid)
    if not h or h.deleted:
        raise ValueError("诉求热点不存在")
    for k, v in data.items():
        setattr(h, k, v)
    db.commit()
    db.refresh(h)
    return {c.name: getattr(h, c.name) for c in h.__table__.columns}


def delete_appeal_hotspot(db: Session, hid: int) -> None:
    h = db.get(AppealHotspot, hid)
    if h:
        h.deleted = 1
        db.commit()
