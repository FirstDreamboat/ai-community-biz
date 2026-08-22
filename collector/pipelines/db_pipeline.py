"""公告入库管道（写入 announcement 表）。"""
import hashlib
import logging
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from collector import settings
from collector.pipelines.dedup import DedupFilter, minhash, url_hash

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)


class AnnouncementItem:
    """标准化公告对象。"""

    def __init__(self, source_id: int, source_url: str, title: str,
                 content: str, raw_html: str = "", publish_time: datetime | None = None,
                 category: str = "tender"):
        self.source_id = source_id
        self.source_url = source_url
        self.title = title
        self.content = content
        self.raw_html = raw_html
        self.publish_time = publish_time or datetime.now()
        self.category = category
        self.fingerprint = self._build_fingerprint()

    def _build_fingerprint(self) -> str:
        u = url_hash(self.source_url)
        c = minhash(self.content or self.title)
        return hashlib.sha256(f"{u}:{c}".encode("utf-8")).hexdigest()


class DbPipeline:
    """入库管道：去重 + 写入数据库。"""

    def __init__(self) -> None:
        self.dedup = DedupFilter()

    def process_item(self, item: AnnouncementItem) -> AnnouncementItem | None:
        if self.dedup.is_dup(item.source_url, item.content or item.title):
            logger.debug("重复公告丢弃: %s", item.title)
            return None

        with Session(engine) as db:
            from sqlalchemy import text

            # 记录采集任务计数（按 source_id 更新最近任务）
            db.execute(
                text(
                    "UPDATE collector_task_log SET new_count = new_count + 1 "
                    "WHERE source_id = :sid AND status = 'running' "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"sid": item.source_id},
            )
            db.execute(
                text(
                    "INSERT INTO announcement "
                    "(fingerprint, source_id, source_url, title, content, raw_html, "
                    "publish_time, crawl_time, parse_status, category) "
                    "VALUES (:fp, :sid, :url, :title, :content, :raw, :pt, :ct, 0, :cat)"
                ),
                {
                    "fp": item.fingerprint,
                    "sid": item.source_id,
                    "url": item.source_url,
                    "title": item.title,
                    "content": item.content,
                    "raw": item.raw_html,
                    "pt": item.publish_time,
                    "ct": datetime.now(),
                    "cat": item.category,
                },
            )
            db.commit()
        return item
