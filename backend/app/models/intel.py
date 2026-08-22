"""智能商机挖掘扩展模型（2026-08-22 新增）。

1. legacy_project      存量项目台账：记录历史在建/在用的对讲/门禁/智能化项目
2. update_opportunity  更新商机：由存量台账按设备生命周期推算的换新商机
3. strategic_customer  战略客户集采台账：物业/房企集采合作与到期预警
4. sales_lead          销售线索：线下报备/展会等渠道线索评分入池
5. competitor_track    竞品中标后续追踪：竞品中标后跟进同项目后续标段
6. appeal_hotspot      12345诉求热点：小区诉求密度聚合出的痛点商机
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
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


class LegacyProject(Base):
    """存量项目台账（设备更新周期推算的基础）。"""
    __tablename__ = "legacy_project"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    community: Mapped[str | None] = mapped_column(String(200), index=True)
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(200))
    systems: Mapped[list | None] = mapped_column(JSON)
    device_brand: Mapped[str | None] = mapped_column(String(100))
    install_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    contract_end_year: Mapped[int | None] = mapped_column(Integer)
    est_budget: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    contact: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0在用 1已换新 2停用/拆除
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class UpdateOpportunity(Base):
    """更新商机：由存量项目按设备生命周期推算生成。"""
    __tablename__ = "update_opportunity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    legacy_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    community: Mapped[str | None] = mapped_column(String(200), index=True)
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    window_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # imminent临期(6-8年) / due换新窗口(8-10年) / overdue超期(>10年)
    recommend_action: Mapped[str | None] = mapped_column(String(500))
    est_budget: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)  # new/following/converted/closed
    owner_name: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class StrategicCustomer(Base):
    """战略客户集采台账：物业/房企集采合作与到期预警。"""
    __tablename__ = "strategic_customer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    coop_type: Mapped[str | None] = mapped_column(String(30))  # 集采/战略/区域代理
    product_lines: Mapped[list | None] = mapped_column(JSON)
    contract_year: Mapped[int | None] = mapped_column(Integer)
    contract_end_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    annual_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    contact: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0正常 1预警 2已流失
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class SalesLead(Base):
    """销售线索：线下渠道线索上报、本地评分、入池跟进。"""
    __tablename__ = "sales_lead"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200))
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    budget: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    stage: Mapped[str | None] = mapped_column(String(30))
    channel: Mapped[str | None] = mapped_column(String(30))
    reporter_name: Mapped[str | None] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    owner_name: Mapped[str | None] = mapped_column(String(50))
    follow_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class CompetitorTrack(Base):
    """竞品中标后续追踪：竞品中标后，跟踪同项目后续标段/增补/维保。"""
    __tablename__ = "competitor_track"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    community: Mapped[str | None] = mapped_column(String(200), index=True)
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    won_at: Mapped[date | None] = mapped_column(Date)
    track_type: Mapped[str | None] = mapped_column(String(30))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="tracking", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class AppealHotspot(Base):
    """12345诉求热点：按小区聚合诉求密度，输出痛点商机。"""
    __tablename__ = "appeal_hotspot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    community: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    appeal_count: Mapped[int] = mapped_column(Integer, default=0)
    hot_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    topics: Mapped[list | None] = mapped_column(JSON)
    sample_titles: Mapped[list | None] = mapped_column(JSON)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    period: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0待跟进 1跟进中 2已转化
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)
