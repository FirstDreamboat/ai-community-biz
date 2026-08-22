"""认证接口。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys import SysUser
from app.schemas.auth import ChangePasswordRequest, LoginRequest, UserInfo
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.authenticate(db, body.username, body.password)


@router.get("/me")
def me(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.get_user_info(db, user.id)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    auth_service.change_password(db, user, body.old_password, body.new_password, ip)
    return {"message": "密码修改成功"}
