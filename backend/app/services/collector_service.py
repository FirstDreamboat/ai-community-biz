"""采集任务服务：触发采集、查询任务记录。"""
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_source import CollectorTaskLog, DataSource

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 项目根目录
COLLECTOR_DIR = PROJECT_ROOT / "collector"


def trigger_collect(db: Session, source_id: int, trigger_type: str = "manual") -> dict:
    """触发单数据源采集。返回 task_id。"""
    source = db.execute(
        select(DataSource).where(DataSource.id == source_id, DataSource.deleted == 0)
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if source.status != 1:
        raise HTTPException(status_code=400, detail="数据源已停用")

    task = CollectorTaskLog(
        source_id=source_id,
        trigger_type=trigger_type,
        started_at=datetime.now(),
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 调用采集服务（后台执行，携带任务 ID 以便回写进度）
    cmd = [
        sys.executable, str(COLLECTOR_DIR / "runner.py"),
        "--source", str(source_id), "--task", str(task.id),
    ]
    try:
        subprocess.Popen(
            cmd,
            cwd=str(COLLECTOR_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("启动采集任务失败 source=%s err=%s", source_id, e)
        task.status = "failed"
        task.error_msg = str(e)
        task.finished_at = datetime.now()
        db.commit()

    return {"task_id": task.id}


def list_tasks(db: Session, source_id: int | None = None, status: str | None = None,
               page: int = 1, page_size: int = 20) -> dict:
    q = select(CollectorTaskLog)
    if source_id:
        q = q.where(CollectorTaskLog.source_id == source_id)
    if status:
        q = q.where(CollectorTaskLog.status == status)
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(CollectorTaskLog.id.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = [
        {
            "id": t.id,
            "source_id": t.source_id,
            "trigger_type": t.trigger_type,
            "started_at": t.started_at,
            "finished_at": t.finished_at,
            "status": t.status,
            "new_count": t.new_count,
            "dup_count": t.dup_count,
            "fail_count": t.fail_count,
            "error_msg": t.error_msg,
            # 前端兼容字段
            "total_found": (t.new_count or 0) + (t.dup_count or 0) + (t.fail_count or 0),
            "total_new": t.new_count,
            "message": t.error_msg,
        }
        for t in rows
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}
