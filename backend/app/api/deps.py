"""API 公共依赖：统一响应封装、权限校验。"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import SysUser

# 权限码常量
PERM_OPP_VIEW = "opp:view"
PERM_OPP_FOLLOW = "opp:follow"
PERM_OPP_ASSIGN = "opp:assign"
PERM_DATA_VIEW = "data:view"
PERM_DATA_MANAGE = "data:manage"
PERM_SYS_USER_VIEW = "sys:user:view"
PERM_SYS_USER_MANAGE = "sys:user:manage"
PERM_SYS_CONFIG_VIEW = "sys:config:view"
PERM_SYS_CONFIG_MANAGE = "sys:config:manage"
PERM_SYS_AUDIT_VIEW = "sys:audit:view"
PERM_KNOWLEDGE_VIEW = "knowledge:view"
PERM_KNOWLEDGE_MANAGE = "knowledge:manage"


def get_client_ip(request: Request) -> str | None:
    """从请求中提取客户端 IP（兼容反向代理）。"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else None


def require_permission(*perm_codes: str):
    """生成依赖：校验当前用户是否拥有任一指定权限（admin 角色直接放行）。"""

    def checker(user: SysUser = Depends(get_current_user)) -> SysUser:
        roles = set(getattr(user, "_roles", None) or [])
        if "admin" in roles:
            return user  # 超管放行
        perms = set(getattr(user, "_perms", None) or [])
        if perm_codes and not (perms & set(perm_codes)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
        return user

    return checker


def ok(data=None, message: str = "success", code: int = 0, trace_id: str = "") -> dict:
    return {"code": code, "message": message, "data": data, "trace_id": trace_id}
