"""数据库连接与会话管理（SQLAlchemy 2.0）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """ORM 模型基类。"""


def get_db():
    """FastAPI 依赖：提供数据库会话。"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
