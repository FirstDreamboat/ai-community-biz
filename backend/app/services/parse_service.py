"""批量解析服务：解析 + AI二次核验 + 评分生成商机。

流程（防止生成假商机）：
  公告 -> DeepSeek/模板解析 -> AI二次核验 ->
    通过(1) -> 生成画像 + 商机（携带核验状态）
    不通过(2)/待人工(3) -> 不生成商机，仅标记公告核验状态

批量解析在线程中运行（DeepSeek 为阻塞式异步调用），任务进度存进程内内存。
"""
import asyncio
import logging
import threading
from datetime import datetime
from uuid import uuid4

from sqlalchemy import or_, select

from app.core.database import SessionLocal
from app.models.announcement import Announcement, ProjectProfile
from app.services import ai_service, competitor_service, scoring_service, verify_service

logger = logging.getLogger(__name__)

# 批量解析任务状态（进程内内存，单任务并发）
BATCH_STATE = {
    "running": False,
    "task_id": None,
    "total": 0,
    "processed": 0,
    "success": 0,      # 核验通过并生成商机
    "rejected": 0,     # 核验不通过
    "manual": 0,       # 待人工复核
    "failed": 0,       # 解析/核验异常
    "started_at": None,
    "finished_at": None,
    "current": None,   # 正在处理的公告id
    "logs": [],        # 最近日志
}
_LOG_LIMIT = 50


def _append_log(msg: str):
    BATCH_STATE["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    if len(BATCH_STATE["logs"]) > _LOG_LIMIT:
        BATCH_STATE["logs"] = BATCH_STATE["logs"][-_LOG_LIMIT:]


def _reset_state():
    BATCH_STATE["running"] = False
    BATCH_STATE["task_id"] = None
    BATCH_STATE["total"] = 0
    BATCH_STATE["processed"] = 0
    BATCH_STATE["success"] = 0
    BATCH_STATE["rejected"] = 0
    BATCH_STATE["manual"] = 0
    BATCH_STATE["failed"] = 0
    BATCH_STATE["started_at"] = None
    BATCH_STATE["finished_at"] = None
    BATCH_STATE["current"] = None
    BATCH_STATE["logs"] = []


def get_batch_state() -> dict:
    return dict(BATCH_STATE)


async def parse_and_verify_one(db, ann: Announcement, with_verify: bool = True) -> dict:
    """解析单条公告 + AI二次核验；核验通过才生成画像与商机。

    返回: {"ann_id", "source", "verify_status", "opportunity_id", "error"}
    """
    ann.parse_error = None
    try:
        result, source = await ai_service.parse_announcement(ann.title, ann.content or "")
    except Exception as e:  # noqa: BLE001
        ann.parse_status = 2
        ann.parse_error = str(e)[:500]
        db.commit()
        return {"ann_id": ann.id, "source": "error", "verify_status": 0,
                "opportunity_id": None, "error": str(e)[:200]}

    verify = {"status": 1, "note": "未启用核验", "detail": {"source": source}}
    if with_verify:
        verify = await verify_service.verify_announcement(
            ann.title, ann.content or "", result, source
        )

    ann.verify_status = verify["status"]
    ann.verify_result = verify["detail"]

    if verify["status"] != 1:
        # 不通过/待人工：不自动生成商机
        ann.parse_status = 1 if verify["status"] == 2 else 3
        db.commit()
        return {"ann_id": ann.id, "source": source, "verify_status": verify["status"],
                "opportunity_id": None, "error": None}

    # 核验通过：upsert 画像并生成/更新商机
    profile_data = ai_service.map_to_profile(result, ann.id)
    profile_data["parsed_by"] = source
    # 用 AI 核验判定的相关度回写画像（更准），供评分/列表使用
    llm_rel = (verify["detail"] or {}).get("suggested_relevance")
    if llm_rel in ("高", "中", "低"):
        profile_data["relevance"] = llm_rel
    profile = db.execute(
        select(ProjectProfile).where(ProjectProfile.announcement_id == ann.id)
    ).scalar_one_or_none()
    if profile is None:
        profile = ProjectProfile(**profile_data)
        db.add(profile)
        db.flush()
    else:
        for k, v in profile_data.items():
            setattr(profile, k, v)
        db.flush()

    opp = scoring_service.generate_opportunity(
        db, profile.id, verify_status=1, verify_note=verify["note"]
    )
    # 竞品监测：核验通过的中标/结果类公告中识别竞品品牌并入库
    try:
        competitor_service.detect_competitors(
            db,
            ann.title,
            ann.content or "",
            profile_id=profile.id,
            announcement_id=ann.id,
            province=profile.province,
            amount=profile.budget,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("竞品监测异常（不影响商机生成）: %s", e)
    ann.parse_status = 1
    db.commit()
    return {"ann_id": ann.id, "source": source, "verify_status": 1,
            "opportunity_id": opp.id, "error": None}


async def _batch_worker(limit: int, reparse_failed: bool, with_verify: bool):
    db = SessionLocal()
    try:
        conds = [Announcement.parse_status == 0]
        if reparse_failed:
            conds.append(Announcement.parse_status == 2)
        # 修复核验盲区：已解析但从未核验（parse_status=1 且 verify_status=0）的公告
        # 一并纳入批量处理，避免永久悬挂在"未核验"状态（此前仅覆盖 parse_status 0/2）
        conds.append(
            (Announcement.parse_status == 1) & (Announcement.verify_status == 0)
        )
        anns = db.execute(
            select(Announcement)
            .where(or_(*conds), Announcement.deleted == 0)
            .order_by(Announcement.id.asc())
            .limit(limit)
        ).scalars().all()

        BATCH_STATE["total"] = len(anns)
        _append_log(f"批量解析开始：待处理 {len(anns)} 条（limit={limit}, reparse_failed={reparse_failed}）")

        for ann in anns:
            if not BATCH_STATE["running"]:  # 支持取消
                _append_log("批量解析被取消")
                break
            BATCH_STATE["current"] = ann.id
            try:
                # 已解析但未核验的公告强制走核验，避免 with_verify=False 时绕过核验直接生成商机
                need_verify = with_verify or (
                    ann.parse_status == 1 and ann.verify_status == 0
                )
                res = await parse_and_verify_one(db, ann, with_verify=need_verify)
                if res["error"]:
                    BATCH_STATE["failed"] += 1
                    _append_log(f"#{ann.id} 解析失败: {res['error']}")
                elif res["verify_status"] == 1:
                    BATCH_STATE["success"] += 1
                    _append_log(f"#{ann.id} 核验通过，已生成商机 opp={res['opportunity_id']}")
                elif res["verify_status"] == 2:
                    BATCH_STATE["rejected"] += 1
                    _append_log(f"#{ann.id} 核验不通过，未生成商机")
                else:
                    BATCH_STATE["manual"] += 1
                    _append_log(f"#{ann.id} 待人工复核，未生成商机")
            except Exception as e:  # noqa: BLE001
                BATCH_STATE["failed"] += 1
                _append_log(f"#{ann.id} 处理异常: {str(e)[:200]}")
            BATCH_STATE["processed"] += 1
            BATCH_STATE["current"] = None

        _append_log(
            f"批量解析完成：成功 {BATCH_STATE['success']}，"
            f"不通过 {BATCH_STATE['rejected']}，待人工 {BATCH_STATE['manual']}，失败 {BATCH_STATE['failed']}"
        )
    finally:
        BATCH_STATE["running"] = False
        BATCH_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        BATCH_STATE["current"] = None
        db.close()


def start_batch_parse(
    limit: int = 30,
    reparse_failed: bool = False,
    with_verify: bool = True,
) -> dict | None:
    """启动后台批量解析。若已有任务在跑则返回 None。"""
    if BATCH_STATE["running"]:
        return None
    _reset_state()
    BATCH_STATE["running"] = True
    BATCH_STATE["task_id"] = uuid4().hex
    BATCH_STATE["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    threading.Thread(
        target=lambda: asyncio.run(_batch_worker(limit, reparse_failed, with_verify)),
        daemon=True,
    ).start()
    return get_batch_state()
