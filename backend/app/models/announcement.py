"""公告与项目画像模型（对应 DBD 3.2 / 3.3）。"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    DECIMAL,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Announcement(Base):
    __tablename__ = "announcement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    raw_html: Mapped[str | None] = mapped_column(Text)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    crawl_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    parse_status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0待解析 1已解析 2失败 3待人工
    verify_status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0未核验 1通过 2不通过 3待人工
    verify_result: Mapped[dict | None] = mapped_column(JSON)  # AI核验详情
    parse_error: Mapped[str | None] = mapped_column(String(500))  # 最近一次解析/核验错误
    category: Mapped[str | None] = mapped_column(String(20))  # tender/property/policy/news
    extra: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class ProjectProfile(Base):
    __tablename__ = "project_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    purchaser: Mapped[str | None] = mapped_column(String(200))
    project_type: Mapped[str | None] = mapped_column(String(50))
    budget: Mapped[Decimal | None] = mapped_column(DECIMAL(14, 2))
    budget_est: Mapped[int] = mapped_column(Integer, default=0)
    bid_deadline: Mapped[datetime | None] = mapped_column(DateTime)
    open_time: Mapped[datetime | None] = mapped_column(DateTime)
    qualification: Mapped[list | None] = mapped_column(JSON)
    tech_params: Mapped[list | None] = mapped_column(JSON)
    household_cnt: Mapped[int | None] = mapped_column(Integer)
    building_cnt: Mapped[int | None] = mapped_column(Integer)
    area: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    contents: Mapped[list | None] = mapped_column(JSON)  # 改造内容标签
    fund_source: Mapped[str | None] = mapped_column(String(20))
    stage: Mapped[str | None] = mapped_column(String(20))
    relevance: Mapped[str | None] = mapped_column(String(10))
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    district: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    parsed_by: Mapped[str | None] = mapped_column(String(50))  # deepseek/template/human
    human_verified: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)
