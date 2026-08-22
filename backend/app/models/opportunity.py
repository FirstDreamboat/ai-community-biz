"""商机、跟进、推送、竞品模型（对应 DBD 3.4-3.7）。"""
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Opportunity(Base):
    __tablename__ = "opportunity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    total_score: Mapped[Decimal] = mapped_column(DECIMAL(5, 1), nullable=False, index=True)
    demand_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    budget_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    region_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    urgency_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    competition_score: Mapped[Decimal | None] = mapped_column(DECIMAL(4, 1))
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str | None] = mapped_column(String(10), index=True)  # high/medium/low
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    verify_status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 0未核验 1通过 2不通过 3待人工
    verify_note: Mapped[str | None] = mapped_column(String(500))  # 核验备注(结论简述)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    assign_time: Mapped[datetime | None] = mapped_column(DateTime)
    recommend_reason: Mapped[str | None] = mapped_column(Text)
    follow_strategy: Mapped[dict | None] = mapped_column(JSON)
    score_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class FollowUpLog(Base):
    __tablename__ = "follow_up_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)
    next_plan: Mapped[str | None] = mapped_column(String(500))
    follow_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PushRecord(Base):
    __tablename__ = "push_record"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "push_channel", "push_date", name="uk_opp_channel_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    push_channel: Mapped[str] = mapped_column(String(20), nullable=False)  # sms/email/webhook
    receiver: Mapped[str] = mapped_column(String(200), nullable=False)
    push_date: Mapped[date] = mapped_column(Date, nullable=False)
    content_snapshot: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_msg: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CompetitorRecord(Base):
    __tablename__ = "competitor_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    announcement_id: Mapped[int | None] = mapped_column(BigInteger)
    profile_id: Mapped[int | None] = mapped_column(BigInteger)
    province: Mapped[str | None] = mapped_column(String(50), index=True)
    result: Mapped[str | None] = mapped_column(String(20))
    amount: Mapped[Decimal | None] = mapped_column(DECIMAL(14, 2))
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
