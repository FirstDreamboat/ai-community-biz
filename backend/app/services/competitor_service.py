"""竞品监测服务：从公告中识别竞品品牌并写入竞品记录。

设计（对应 DLD 6.3 竞品监测）：
  1. 采集公告经解析核验通过后，调用 detect_competitors 检查标题/内容；
  2. 仅对「中标/成交/候选人/结果」类公告做竞品记录（普通招标公告无竞品信息，
     避免把招标公告误记为竞品动态）；
  3. 关键词库来自 sys_config.competitor.keywords，可在前端维护；
  4. 同一公告 + 同一竞品 去重，避免重复入库。
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select

from app.models.opportunity import CompetitorRecord
from app.models.sys import SysConfig

logger = logging.getLogger(__name__)

# 结果类公告特征词：仅这类公告包含竞品中标/投标信息
RESULT_KEYWORDS = ("中标", "成交", "定标", "中选", "候选人", "评标结果", "中标签约", "结果公告", "中标公示")
# 明确中标类特征（优先级高于候选）
_WIN_KEYWORDS = ("中标", "成交", "定标", "中选", "中标签约", "中标结果", "中标公示")
_CANDIDATE_KEYWORDS = ("候选人", "评标结果")

_KEY = "competitor.keywords"


def get_keywords(db) -> list[str]:
    """读取竞品监测关键词配置。"""
    row = db.execute(
        select(SysConfig).where(SysConfig.config_key == _KEY)
    ).scalar_one_or_none()
    if not row or not row.config_value:
        return []
    try:
        data = json.loads(row.config_value)
        return [k for k in data if isinstance(k, str) and k.strip()]
    except (ValueError, TypeError):
        logger.warning("竞品关键词配置解析失败: %s", row.config_value)
        return []


def save_keywords(db, keywords: list, user_id: int | None = None) -> list[str]:
    """保存竞品监测关键词配置（去空、去重）。"""
    cleaned: list[str] = []
    for k in keywords or []:
        k = str(k or "").strip()
        if k and k not in cleaned:
            cleaned.append(k)
    row = db.execute(
        select(SysConfig).where(SysConfig.config_key == _KEY)
    ).scalar_one_or_none()
    if row is None:
        row = SysConfig(
            config_key=_KEY,
            config_value=json.dumps(cleaned, ensure_ascii=False),
            remark="竞品监测品牌关键词",
        )
        db.add(row)
    else:
        row.config_value = json.dumps(cleaned, ensure_ascii=False)
    if user_id:
        row.updated_by = user_id
    db.commit()
    return cleaned


def detect_competitors(
    db,
    title: str,
    content: str,
    *,
    profile_id: int | None = None,
    announcement_id: int | None = None,
    province: str | None = None,
    amount=None,
) -> list[CompetitorRecord]:
    """从公告标题/内容中识别竞品品牌并写入竞品记录。

    仅对「中标/成交/候选人/结果」类公告记录；同一公告+同一竞品去重。
    返回本次新建的记录列表。
    """
    text = f"{title or ''}\n{content or ''}"
    # 非结果类公告 -> 不监测（招标/采购公告无竞品中标信息）
    if not any(k in text for k in RESULT_KEYWORDS):
        return []

    keywords = get_keywords(db)
    if not keywords:
        return []

    # 结果类型：候选人/评标结果公示 优先判定为「投标」（尚未定标）；
    # 其余含明确中标词（中标结果/成交/定标等）判为「中标」。
    if any(k in text for k in _CANDIDATE_KEYWORDS):
        result = "投标"
    elif any(k in text for k in _WIN_KEYWORDS):
        result = "中标"
    else:
        result = "投标"

    created: list[CompetitorRecord] = []
    for kw in keywords:
        if kw not in text:
            continue
        # 去重：同一公告 + 同一竞品
        exists = db.execute(
            select(CompetitorRecord).where(
                CompetitorRecord.announcement_id == announcement_id,
                CompetitorRecord.competitor == kw,
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        rec = CompetitorRecord(
            competitor=kw,
            announcement_id=announcement_id,
            profile_id=profile_id,
            province=province,
            result=result,
            amount=amount,
            detected_at=datetime.now(),
        )
        db.add(rec)
        created.append(rec)
    if created:
        db.commit()
        logger.info("竞品监测：公告#%s 命中 %d 条竞品记录", announcement_id, len(created))
    return created
