"""安全模块：密码哈希、JWT 签发与校验、当前用户依赖。"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.sys import SysUser

security_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    """BCrypt 哈希。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 Token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> SysUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    payload = decode_token(credentials.credentials)
    user_id = int(payload.get("sub", 0))
    user = db.execute(select(SysUser).where(SysUser.id == user_id)).scalar_one_or_none()
    if user is None or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已停用")
    # 加载角色码与权限码（供 require_permission 校验）
    from app.models.sys import SysPermission, SysRole, SysRolePermission, SysUserRole

    role_rows = db.execute(
        select(SysRole.role_code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user.id)
    ).all()
    perm_rows = db.execute(
        select(SysPermission.perm_code)
        .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
        .join(SysRole, SysRole.id == SysRolePermission.role_id)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user.id)
        .distinct()
    ).all()
    user._roles = {r[0] for r in role_rows}
    user._perms = {p[0] for p in perm_rows}
    return user
