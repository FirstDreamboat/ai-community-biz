"""数据源与采集任务记录模型（对应 DBD 3.1 / 3.14）。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # gov/property/policy/news/api
    base_url: Mapped[str | None] = mapped_column(String(500))
    list_pages: Mapped[list | None] = mapped_column(JSON, default=list)
    spider_class: Mapped[str | None] = mapped_column(String(100))
    keywords: Mapped[list | None] = mapped_column(JSON)
    regions: Mapped[list | None] = mapped_column(JSON)
    schedule_cron: Mapped[str | None] = mapped_column(String(50))
    proxy_enabled: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_run_status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class CollectorTaskLog(Base):
    __tablename__ = "collector_task_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    trigger_type: Mapped[str | None] = mapped_column(String(20))  # schedule/manual
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String(20))  # running/success/failed
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    dup_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
