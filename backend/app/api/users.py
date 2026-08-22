"""系统管理接口：用户、角色、配置、审计。"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    PERM_SYS_AUDIT_VIEW,
    PERM_SYS_CONFIG_MANAGE,
    PERM_SYS_CONFIG_VIEW,
    PERM_SYS_USER_MANAGE,
    PERM_SYS_USER_VIEW,
    ok,
    require_permission,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import (
    AuditLog,
    SysConfig,
    SysPermission,
    SysRole,
    SysRolePermission,
    SysUser,
    SysUserRole,
)
from app.services import audit_service, auth_service

router = APIRouter(prefix="", tags=["系统管理"])


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    real_name: str | None = None
    dept: str | None = None
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    real_name: str | None = None
    dept: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    role_codes: list[str] | None = None


class RoleCreate(BaseModel):
    role_name: str = Field(min_length=1, max_length=50)
    role_code: str = Field(min_length=1, max_length=50)
    remark: str | None = None
    perm_codes: list[str] = []


class RoleUpdate(BaseModel):
    role_name: str = Field(min_length=1, max_length=50)
    remark: str | None = None
    perm_codes: list[str] = []


class ConfigUpdate(BaseModel):
    config_value: str


# ---------- 用户 ----------
@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_SYS_USER_VIEW)),
):
    rows = db.execute(select(SysUser).where(SysUser.deleted == 0)).scalars().all()
    # 组装每个用户的角色
    role_map: dict[int, list[str]] = {}
    pairs = db.execute(
        select(SysUserRole.user_id, SysRole.role_code)
        .join(SysRole, SysRole.id == SysUserRole.role_id)
    ).all()
    for user_id, code in pairs:
        role_map.setdefault(user_id, []).append(code)
    items = [
        {"id": u.id, "username": u.username, "real_name": u.real_name,
         "dept": u.dept, "status": u.status, "last_login_at": u.last_login_at,
         "roles": role_map.get(u.id, [])}
        for u in rows
    ]
    return ok(items)


@router.post("/users")
def create_user(
    body: UserCreate,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    new_user = auth_service.create_user(
        db, body.username, body.password, body.real_name or "", body.dept or ""
    )
    for code in body.role_codes:
        role = db.execute(select(SysRole).where(SysRole.role_code == code)).scalar_one_or_none()
        if role:
            db.add(SysUserRole(user_id=new_user.id, role_id=role.id))
    db.commit()
    audit_service.write_audit(db, user.id, "create_user", "system", str(new_user.id))
    return ok({"id": new_user.id})


@router.put("/users/{uid}")
def update_user(
    uid: int,
    body: UserUpdate,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    u = db.execute(select(SysUser).where(SysUser.id == uid, SysUser.deleted == 0)).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.real_name is not None:
        u.real_name = body.real_name
    if body.dept is not None:
        u.dept = body.dept
    if body.status is not None:
        if u.username == "admin" and body.status != 1:
            raise HTTPException(status_code=400, detail="不能停用内置管理员账号")
        u.status = body.status
    if body.password:
        u.password_hash = auth_service.hash_password(body.password)
    if body.role_codes is not None:
        if u.username == "admin":
            raise HTTPException(status_code=400, detail="内置管理员角色不允许修改")
        db.execute(SysUserRole.__table__.delete().where(SysUserRole.user_id == u.id))
        for code in body.role_codes:
            role = db.execute(select(SysRole).where(SysRole.role_code == code)).scalar_one_or_none()
            if role:
                db.add(SysUserRole(user_id=u.id, role_id=role.id))
    db.commit()
    audit_service.write_audit(db, user.id, "update_user", "system", str(uid))
    return ok()


@router.delete("/users/{uid}")
def delete_user(
    uid: int,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    u = db.execute(select(SysUser).where(SysUser.id == uid)).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.username == "admin":
        raise HTTPException(status_code=400, detail="内置管理员不允许删除")
    u.deleted = 1
    db.commit()
    audit_service.write_audit(db, user.id, "delete_user", "system", str(uid))
    return ok()


# ---------- 角色 ----------
@router.get("/permissions")
def list_permissions(
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_SYS_USER_VIEW)),
):
    rows = db.execute(select(SysPermission).order_by(SysPermission.module, SysPermission.id)).scalars().all()
    return ok([{"id": p.id, "perm_code": p.perm_code, "perm_name": p.perm_name,
                "module": p.module} for p in rows])


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_SYS_USER_VIEW)),
):
    rows = db.execute(select(SysRole)).scalars().all()
    perm_map: dict[int, list[str]] = {}
    pairs = db.execute(
        select(SysRolePermission.role_id, SysPermission.perm_code)
        .join(SysPermission, SysPermission.id == SysRolePermission.permission_id)
    ).all()
    for role_id, code in pairs:
        perm_map.setdefault(role_id, []).append(code)
    return ok([{"id": r.id, "role_name": r.role_name, "role_code": r.role_code,
                "remark": r.remark, "perm_codes": perm_map.get(r.id, [])} for r in rows])


@router.post("/roles")
def create_role(
    body: RoleCreate,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    exists = db.execute(select(SysRole).where(SysRole.role_code == body.role_code)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="角色编码已存在")
    role = SysRole(role_name=body.role_name, role_code=body.role_code, remark=body.remark)
    db.add(role)
    db.flush()
    for code in body.perm_codes:
        p = db.execute(select(SysPermission).where(SysPermission.perm_code == code)).scalar_one_or_none()
        if p:
            db.add(SysRolePermission(role_id=role.id, permission_id=p.id))
    db.commit()
    audit_service.write_audit(db, user.id, "create_role", "system", str(role.id))
    return ok({"id": role.id})


@router.put("/roles/{rid}")
def update_role(
    rid: int,
    body: RoleUpdate,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    role = db.execute(select(SysRole).where(SysRole.id == rid)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.role_code == "admin":
        raise HTTPException(status_code=400, detail="内置管理员角色不允许修改")
    role.role_name = body.role_name
    if body.remark is not None:
        role.remark = body.remark
    db.execute(SysRolePermission.__table__.delete().where(SysRolePermission.role_id == rid))
    for code in body.perm_codes:
        p = db.execute(select(SysPermission).where(SysPermission.perm_code == code)).scalar_one_or_none()
        if p:
            db.add(SysRolePermission(role_id=rid, permission_id=p.id))
    db.commit()
    audit_service.write_audit(db, user.id, "update_role", "system", str(rid))
    return ok()


@router.delete("/roles/{rid}")
def delete_role(
    rid: int,
    user: SysUser = Depends(require_permission(PERM_SYS_USER_MANAGE)),
    db: Session = Depends(get_db),
):
    role = db.execute(select(SysRole).where(SysRole.id == rid)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.role_code == "admin":
        raise HTTPException(status_code=400, detail="内置管理员角色不允许删除")
    # 级联清理关联
    db.execute(SysRolePermission.__table__.delete().where(SysRolePermission.role_id == rid))
    db.execute(SysUserRole.__table__.delete().where(SysUserRole.role_id == rid))
    db.delete(role)
    db.commit()
    audit_service.write_audit(db, user.id, "delete_role", "system", str(rid))
    return ok()


# ---------- 配置 ----------
@router.get("/configs/{key}")
def get_config(
    key: str,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_SYS_CONFIG_VIEW)),
):
    row = db.execute(select(SysConfig).where(SysConfig.config_key == key)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    try:
        value = json.loads(row.config_value) if row.config_value else None
    except json.JSONDecodeError:
        value = row.config_value
    return ok({"key": key, "value": value})


@router.put("/configs/{key}")
def update_config(
    key: str,
    body: ConfigUpdate,
    user: SysUser = Depends(require_permission(PERM_SYS_CONFIG_MANAGE)),
    db: Session = Depends(get_db),
):
    row = db.execute(select(SysConfig).where(SysConfig.config_key == key)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    row.config_value = body.config_value
    row.updated_by = user.id
    db.commit()
    audit_service.write_audit(db, user.id, "update_config", "system", key)
    return ok()


# ---------- 审计 ----------
@router.get("/audit-logs")
def list_audit_logs(
    user_id: int | None = None,
    module: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_SYS_AUDIT_VIEW)),
):
    q = select(AuditLog)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if module:
        q = q.where(AuditLog.module == module)
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(AuditLog.id.desc())
                     .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = [
        {"id": a.id, "user_id": a.user_id, "action": a.action, "module": a.module,
         "target_id": a.target_id, "detail": a.detail, "ip": a.ip, "created_at": a.created_at}
        for a in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": items})
