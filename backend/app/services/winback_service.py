"""中标反推线索服务（2026-10-10 新增）。

从已采集的"中标/成交"公告中反向挖掘销售线索：
1. 中标公告会被商机核验正确拒绝（verify_status=2，"结果公示不可跟进"），
   但它是线索金矿——业主方有持续改造需求，中标总包商有智能化分包需求；
2. 流程：关键词筛选 -> 行业相关性预过滤 -> DeepSeek 结构化提取
   （项目/业主/中标人/金额/区域/业务相关性/跟进建议）-> 入库 sales_lead；
3. channel 固定"中标反推"，detail 记录中标人与公告链接形成证据链；
4. 按公告 URL 去重，同一公告不重复挖掘。
"""
import json
import logging

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.announcement import Announcement
from app.models.intel import SalesLead
from app.services import llm_quota

logger = logging.getLogger(__name__)

# 中标/成交类公告标题特征（商机核验阶段被正确拒绝的那批）
WIN_ANNOUNCEMENT_KEYWORDS = (
    "中标公告", "中标结果", "成交公告", "成交结果", "结果公示",
    "评标结果", "中标候选人", "合同公告", "履约公告",
)

# 行业相关性预过滤：命中才送 LLM，节省配额
INDUSTRY_HINT_KEYWORDS = (
    "智能化", "弱电", "综合布线", "系统集成", "安防", "监控", "视频监控",
    "门禁", "对讲", "楼宇对讲", "可视对讲", "智慧社区", "智慧园区", "智慧楼宇",
    "智慧医院", "智慧校园", "数字校园", "信息发布", "广播", "机房", "周界",
    "停车场", "道闸", "人脸识别", "物联网", "信息化", "老旧小区", "旧改",
    "城市更新", "医院", "学校", "职业学院", "大学",
)

_EXTRACT_PROMPT = """你是招投标线索挖掘助手。以下是政府采购/招投标"中标（成交）结果公告"文本。
请提取结构化信息并输出 JSON（不要输出其他内容）：
{
  "project_name": "项目名称",
  "owner": "业主/采购人单位",
  "winner": "中标（成交）供应商",
  "winner_type": "中标人类型（智能化集成商/建筑总包/设备厂商/其他）",
  "amount_wanyuan": 中标金额（万元，数字，无法识别填 null）,
  "province": "省份（如 安徽省；无法识别填 null）",
  "city": "城市（无法识别填 null）",
  "relevance": "与楼宇对讲/门禁/智慧社区/智慧医院等智能化设备供应业务的相关性（高/中/低）。参考：智能化工程分包、后续标段、同类项目扩建为高；纯土建/货物采购与智能化无关为低",
  "follow_hint": "一句话跟进建议（面向楼宇对讲设备厂商销售）"
}"""


async def _extract_with_deepseek(text: str) -> dict:
    """调用 DeepSeek 提取中标公告结构化信息。失败抛异常。"""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY")
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": f"公告文本：\n{text[:6000]}\n\n请输出JSON。"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 800,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    llm_quota.record_usage()
    parsed = json.loads(content)
    return parsed if isinstance(parsed, dict) else {}


def _candidate_announcements(db: Session, limit: int) -> list[Announcement]:
    """筛选待挖掘的中标公告：关键词命中 + 行业预过滤 + 按相关性排序 + 未挖掘过。"""
    like_conds = [Announcement.title.like(f"%{k}%") for k in WIN_ANNOUNCEMENT_KEYWORDS]
    q = (
        select(Announcement)
        .where(
            Announcement.deleted == 0,
            Announcement.parse_status.in_([1, 3]),  # 已解析/待人工，跳过纯失败
            or_(*like_conds),
        )
        # MySQL 无 NULLS LAST：用 is_(None) 让空时间排最后
        .order_by(
            Announcement.publish_time.is_(None),
            Announcement.publish_time.desc(),
            Announcement.id.desc(),
        )
        .limit(300)  # 粗筛池，再按行业相关性排序取最优
    )
    rows = db.execute(q).scalars().all()

    # 行业相关性预过滤 + 排序：命中关键词越多越优先送 LLM（节省配额、提高命中）
    scored: list[tuple[int, Announcement]] = []
    for a in rows:
        text = f"{a.title or ''} {a.content or ''}"
        hits = sum(1 for k in INDUSTRY_HINT_KEYWORDS if k in text)
        if hits > 0:
            scored.append((hits, a))
    scored.sort(key=lambda t: (-t[0], -(t[1].id or 0)))
    candidates = [a for _, a in scored][:limit]
    return candidates


def _already_mined(db: Session, source_url: str) -> bool:
    """同一公告（URL）是否已生成过线索。"""
    if not source_url:
        return False
    row = db.execute(
        select(SalesLead.id).where(
            SalesLead.deleted == 0,
            SalesLead.detail.like(f"%{source_url}%"),
        ).limit(1)
    ).scalar()
    return row is not None


def _build_detail(info: dict, source_url: str) -> str:
    lines = []
    if info.get("winner"):
        lines.append(f"中标人：{info['winner']}（{info.get('winner_type') or '未知类型'}）")
    if info.get("amount_wanyuan") is not None:
        lines.append(f"中标金额：{info['amount_wanyuan']}万元")
    if info.get("owner"):
        lines.append(f"业主/采购人：{info['owner']}")
    if info.get("follow_hint"):
        lines.append(f"跟进建议：{info['follow_hint']}")
    lines.append(f"来源公告：{source_url or '无链接'}")
    return "\n".join(lines)


async def mine_winback_leads(db: Session, limit: int = 8) -> dict:
    """从中标公告挖掘销售线索。返回统计 dict。"""
    if not llm_quota.is_llm_available():
        return {"scanned": 0, "created": 0, "skipped": 0, "failed": 0,
                "message": "今日DeepSeek额度已用尽，明日再试"}

    candidates = _candidate_announcements(db, limit)
    created = skipped = failed = 0
    for ann in candidates:
        if created >= limit:
            break
        try:
            if _already_mined(db, ann.source_url or ""):
                skipped += 1
                continue
            info = await _extract_with_deepseek(f"{ann.title}\n{ann.content or ''}")
            relevance = (info.get("relevance") or "低").strip()
            if relevance not in ("高", "中"):
                # 与智能化业务无关的中标公告，标记跳过（写一条空线索会污染池子）
                skipped += 1
                continue
            lead = SalesLead(
                title=f"【中标反推】{info.get('project_name') or ann.title[:80]}",
                customer_name=info.get("owner") or None,
                province=info.get("province") or None,
                city=info.get("city") or None,
                budget=info.get("amount_wanyuan"),
                stage="中标公示",
                channel="中标反推",
                detail=_build_detail(info, ann.source_url or ""),
                status="new",
            )
            db.add(lead)
            db.commit()
            created += 1
            logger.info("中标反推线索已生成 ann=%s lead=%s", ann.id, lead.id)
        except Exception as e:  # noqa: BLE001
            failed += 1
            logger.warning("中标反推挖掘失败 ann=%s: %s", ann.id, e)
            db.rollback()
    return {"scanned": len(candidates), "created": created,
            "skipped": skipped, "failed": failed}
