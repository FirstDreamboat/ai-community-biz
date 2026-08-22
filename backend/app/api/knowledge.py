"""产品知识库接口。"""
import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    PERM_KNOWLEDGE_MANAGE,
    PERM_KNOWLEDGE_VIEW,
    ok,
    require_permission,
)
from app.core.database import get_db
from app.models.knowledge import PolicyInfo, ProductKnowledge
from app.models.sys import SysUser
from app.schemas.data_source import KnowledgeCreate, KnowledgeUpdate, PolicyCreate, PolicyUpdate

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("")
def list_knowledge(
    category: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_VIEW)),
):
    q = select(ProductKnowledge)
    if category:
        q = q.where(ProductKnowledge.category == category)
    if keyword:
        q = q.where(ProductKnowledge.title.like(f"%{keyword}%"))
    total = len(db.execute(q).scalars().all())
    rows = db.execute(q.order_by(ProductKnowledge.id).offset((page - 1) * page_size)
                     .limit(page_size)).scalars().all()
    items = [
        {"id": k.id, "title": k.title, "category": k.category,
         "content": k.content, "tags": k.tags or [], "status": k.status}
        for k in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("/reindex")
def reindex_knowledge(
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    """重建知识库索引。

    未接入外部 embedding 服务时为每条启用知识生成稳定的文本指纹 vector_id
    （基于 title+tags+content 归一化哈希），并支持关键词命中统计。
    """
    rows = db.execute(
        select(ProductKnowledge).where(ProductKnowledge.status == 1)
    ).scalars().all()

    total, updated = 0, 0
    for k in rows:
        text = " ".join(filter(None, [k.title, " ".join(k.tags or []), k.content]))
        norm = re.sub(r"\s+", "", text or "").lower()
        fingerprint = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]
        if k.vector_id != fingerprint:
            k.vector_id = fingerprint
            updated += 1
        total += 1
    db.commit()
    return ok({"total": total, "updated": updated, "mode": "text-fingerprint"})


@router.post("")
def create_knowledge(
    body: KnowledgeCreate,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    k = ProductKnowledge(**body.model_dump())
    db.add(k)
    db.commit()
    db.refresh(k)
    return ok({"id": k.id})


@router.put("/{kid}")
def update_knowledge(
    kid: int,
    body: KnowledgeUpdate,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    k = db.execute(select(ProductKnowledge).where(ProductKnowledge.id == kid)).scalar_one_or_none()
    if k is None:
        raise HTTPException(status_code=404, detail="知识不存在")
    for field, value in body.model_dump().items():
        setattr(k, field, value)
    db.commit()
    return ok({"id": k.id})


@router.delete("/{kid}")
def disable_knowledge(
    kid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    k = db.execute(select(ProductKnowledge).where(ProductKnowledge.id == kid)).scalar_one_or_none()
    if k is None:
        raise HTTPException(status_code=404, detail="知识不存在")
    k.status = 0
    db.commit()
    return ok()


# ---------- 政策信息库（对应 DBD 3.9 policy_info） ----------


@router.get("/policies")
def list_policies(
    level: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_VIEW)),
):
    q = select(PolicyInfo)
    if level:
        q = q.where(PolicyInfo.level == level)
    if region:
        q = q.where(PolicyInfo.region.like(f"%{region}%"))
    if keyword:
        q = q.where(PolicyInfo.title.like(f"%{keyword}%"))
    total = len(db.execute(q).scalars().all())
    rows = db.execute(
        q.order_by(PolicyInfo.publish_time.is_(None), PolicyInfo.publish_time.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [
        {"id": p.id, "title": p.title, "level": p.level, "region": p.region,
         "content": p.content, "publish_time": p.publish_time}
        for p in rows
    ]
    return ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("/policies")
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    p = PolicyInfo(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok({"id": p.id})


@router.put("/policies/{pid}")
def update_policy(
    pid: int,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    p = db.execute(select(PolicyInfo).where(PolicyInfo.id == pid)).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="政策不存在")
    for field, value in body.model_dump().items():
        setattr(p, field, value)
    db.commit()
    return ok({"id": p.id})


@router.delete("/policies/{pid}")
def delete_policy(
    pid: int,
    db: Session = Depends(get_db),
    _: SysUser = Depends(require_permission(PERM_KNOWLEDGE_MANAGE)),
):
    p = db.execute(select(PolicyInfo).where(PolicyInfo.id == pid)).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="政策不存在")
    db.delete(p)
    db.commit()
    return ok()
