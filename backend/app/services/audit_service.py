"""审计日志服务。"""
from sqlalchemy.orm import Session

from app.models.sys import AuditLog


def write_audit(
    db: Session,
    user_id: int | None,
    action: str,
    module: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            target_id=target_id,
            detail=detail,
            ip=ip,
        )
    )
    db.commit()
