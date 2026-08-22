"""商机评分引擎：三步式匹配 + 五维加权评分（对应 ADD 5.3.1 / DLD 5）。"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.announcement import ProjectProfile
from app.models.knowledge import ProductKnowledge
from app.models.office import Office
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

# 产品能力标签 → 需求标签映射（第一轮粗匹配的简化实现）
# 覆盖狄耐克主营：楼宇对讲 / 智能家居 / 智慧社区 / 医护对讲 / 安防门禁 / 停车管理
CATEGORY_NEED_MAP = {
    "对讲系统": ["对讲系统", "楼宇对讲", "可视对讲", "呼叫对讲", "门禁"],
    "智能家居": ["智能家居", "智能面板", "智能网关", "智能开关", "智能灯光", "智能场景", "智慧生活"],
    "医护对讲": ["医护对讲", "病房呼叫", "护理呼叫", "医护", "病区", "ICU", "医院", "医疗"],
    "门禁": ["门禁", "智能门禁", "人脸识别"],
    "安防系统": ["安防", "监控", "紧急求助", "一键报警", "周界报警"],
    "停车管理": ["停车", "智慧停车", "车位"],
    "智能化工程": ["智能化工程", "智能化", "弱电", "弱电工程", "综合布线", "系统集成", "楼宇自控", "节能改造"],
    "智慧社区": ["智慧社区", "社区平台", "智能化"],
}


def load_weights(db: Session) -> dict:
    """从系统配置加载评分权重，失败时回退默认值。"""
    from app.models.sys import SysConfig

    row = db.execute(
        select(SysConfig).where(SysConfig.config_key == "scoring.weights")
    ).scalar_one_or_none()
    if row and row.config_value:
        try:
            return json.loads(row.config_value)
        except json.JSONDecodeError:
            logger.warning("scoring.weights 配置解析失败，使用默认权重")
    return dict(settings.SCORING_WEIGHTS)


def demand_match_score(
    profile: ProjectProfile, knowledge: list[ProductKnowledge]
) -> tuple[float, list]:
    """需求匹配度（0-1）：标签粗匹配 + 向量深度匹配的简化实现。"""
    needs = set(profile.contents or [])
    if not needs:
        return 0.0, []

    # 第一轮：需求标签与产品标签的 Jaccard 匹配
    best_jaccard = 0.0
    matched_tags = []
    for k in knowledge:
        tags = set(k.tags or [])
        product_needs = set(CATEGORY_NEED_MAP.get(k.category, []))
        union = needs | product_needs
        inter = needs & product_needs
        # 结合知识标签
        inter |= needs & tags
        if union:
            j = len(inter) / len(union)
            if j > best_jaccard:
                best_jaccard = j
                matched_tags = list(inter)
    return best_jaccard, matched_tags


def budget_score(budget: Decimal | None) -> float:
    """预算规模计分（0-20）。"""
    if budget is None:
        return 0.0
    b = float(budget)
    if b >= 1000:
        return 20.0
    if b >= 500:
        return 16.0
    if b >= 100:
        return 12.0
    if b > 0:
        return 6.0
    return 0.0


def region_score(profile: ProjectProfile, db: Session) -> float:
    """区域覆盖计分（0-15）：第三轮区域匹配，city 精确优先，降级到 province。"""
    if not profile.province:
        return 5.0

    def _pick(q):
        # cover 直营优先于 radiate/经销
        rows = db.execute(q.order_by(
            (Office.cover_type == "cover").desc(), Office.id
        )).scalars().all()
        return rows[0] if rows else None

    # 第一优先：省 + 市 精确匹配
    if profile.city:
        office = _pick(select(Office).where(
            Office.province == profile.province,
            Office.city == profile.city,
            Office.status == 1,
        ))
        if office is not None:
            return 15.0 if office.cover_type == "cover" else 10.5
    # 第二优先：仅省匹配
    office = _pick(select(Office).where(
        Office.province == profile.province,
        Office.status == 1,
    ))
    if office is not None:
        return 12.0 if office.cover_type == "cover" else 8.0
    return 4.5


def urgency_score(profile: ProjectProfile) -> float:
    """时间紧迫度（0-15）。"""
    if not profile.bid_deadline:
        return 5.0
    days = (profile.bid_deadline - datetime.now()).days
    if days <= 7:
        return 15.0
    if days <= 30:
        return 12.0
    if days <= 90:
        return 8.0
    return 5.0


def competition_score(profile: ProjectProfile, db: Session) -> float:
    """竞争态势（0-10）：按竞品记录数计分。"""
    from app.models.opportunity import CompetitorRecord

    count = db.execute(
        select(func.count()).select_from(CompetitorRecord).where(
            CompetitorRecord.profile_id == profile.id,
            CompetitorRecord.result == "中标",
        )
    ).scalar_one() or 0
    if count >= 2:
        return 4.0
    if count == 1:
        return 7.0
    return 10.0


def score_profile(db: Session, profile: ProjectProfile, rules_version: str = "v1") -> dict:
    """对单个项目画像计算商机评分。"""
    knowledge = db.execute(
        select(ProductKnowledge).where(ProductKnowledge.status == 1)
    ).scalars().all()

    demand, matched_tags = demand_match_score(profile, knowledge)
    weights = load_weights(db)
    w = {
        "demand": float(weights.get("demand", 40)),
        "budget": float(weights.get("budget", 20)),
        "region": float(weights.get("region", 15)),
        "urgency": float(weights.get("urgency", 15)),
        "competition": float(weights.get("competition", 10)),
    }
    w_sum = sum(w.values()) or 100.0
    # 归一化权重
    w = {k: v / w_sum * 100 for k, v in w.items()}

    s_demand = round(demand * w["demand"], 1)
    s_budget = round(budget_score(profile.budget) / 20 * w["budget"], 1)
    s_region = round(region_score(profile, db) / 15 * w["region"], 1)
    s_urgency = round(urgency_score(profile) / 15 * w["urgency"], 1)
    s_competition = round(competition_score(profile, db) / 10 * w["competition"], 1)

    total = round(s_demand + s_budget + s_region + s_urgency + s_competition, 1)
    level = "high" if total >= 70 else ("medium" if total >= 40 else "low")

    strategy = {
        "level": level,
        "actions": (
            ["立即联系招标方", "准备定制化方案", "24小时内完成首次跟进"]
            if level == "high"
            else ["进一步调研项目信息", "准备标准方案" ]
            if level == "medium"
            else ["持续关注", "定期复查（每周）"]
        ),
    }

    return {
        "total_score": Decimal(str(total)),
        "demand_score": Decimal(str(s_demand)),
        "budget_score": Decimal(str(s_budget)),
        "region_score": Decimal(str(s_region)),
        "urgency_score": Decimal(str(s_urgency)),
        "competition_score": Decimal(str(s_competition)),
        "rules_version": rules_version,
        "level": level,
        "recommend_reason": f"需求匹配标签: {matched_tags or '待补充'}",
        "follow_strategy": strategy,
    }


def generate_opportunity(
    db: Session,
    profile_id: int,
    verify_status: int = 0,
    verify_note: str | None = None,
) -> Opportunity:
    """为项目画像生成/更新商机记录。

    verify_status: 0未核验 1通过 2不通过 3待人工（默认0，仅核验通过时传入1）
    verify_note: 核验备注（结论简述）
    """
    profile = db.execute(
        select(ProjectProfile).where(ProjectProfile.id == profile_id)
    ).scalar_one_or_none()
    if profile is None:
        raise ValueError(f"画像不存在: {profile_id}")

    result = score_profile(db, profile)

    opp = db.execute(
        select(Opportunity).where(Opportunity.profile_id == profile_id)
    ).scalar_one_or_none()
    if opp is None:
        opp = Opportunity(
            profile_id=profile_id,
            score_at=datetime.now(),
            verify_status=verify_status,
            verify_note=verify_note,
            **result,
        )
        db.add(opp)
    else:
        for k, v in result.items():
            setattr(opp, k, v)
        opp.score_at = datetime.now()
        opp.verify_status = verify_status
        opp.verify_note = verify_note
    db.commit()
    db.refresh(opp)
    return opp
