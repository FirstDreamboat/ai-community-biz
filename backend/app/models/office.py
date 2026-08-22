"""办事处/经销网点覆盖表（对应 DBD 04_regions_offices.sql）。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Office(Base):
    __tablename__ = "office"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    office_name: Mapped[str] = mapped_column(String(100), nullable=False)
    office_type: Mapped[str] = mapped_column(String(20), default="直属")  # 直属/经销
    province: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(50))
    cover_type: Mapped[str] = mapped_column(String(20), default="cover")  # cover/radiate/none
    address: Mapped[str | None] = mapped_column(String(300))
    contact: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
