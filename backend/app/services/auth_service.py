"""认证与用户信息服务。"""
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.sys import (
    AuditLog,
    SysPermission,
    SysRole,
    SysRolePermission,
    SysUser,
    SysUserRole,
)
from app.schemas.auth import LoginResponse, UserInfo


def authenticate(db: Session, username: str, password: str) -> LoginResponse:
    user = db.execute(select(SysUser).where(SysUser.username == username)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    user.last_login_at = datetime.now()
    db.commit()

    token = create_access_token(user.id, user.username)
    return LoginResponse(
        token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=get_user_info(db, user.id),
    )


def get_user_info(db: Session, user_id: int) -> UserInfo:
    user = db.execute(select(SysUser).where(SysUser.id == user_id)).scalar_one()
    rows = db.execute(
        select(SysRole.role_code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id)
    ).all()
    roles = [r[0] for r in rows]

    perms = db.execute(
        select(SysPermission.perm_code)
        .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
        .join(SysRole, SysRole.id == SysRolePermission.role_id)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id)
        .distinct()
    ).all()
    return UserInfo(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        dept=user.dept,
        roles=roles,
        permissions=[p[0] for p in perms],
    )


def change_password(
    db: Session, user: SysUser, old_password: str, new_password: str, ip: str | None = None
) -> None:
    """修改当前用户密码：校验旧密码 → 更新哈希 → 记录审计。"""
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if old_password == new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(new_password)
    db.add(
        AuditLog(
            user_id=user.id,
            action="change_password",
            module="auth",
            detail={"username": user.username},
            ip=ip,
        )
    )
    db.commit()


def create_user(db: Session, username: str, password: str, real_name: str, dept: str) -> SysUser:
    exists = db.execute(select(SysUser).where(SysUser.username == username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = SysUser(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        dept=dept,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
