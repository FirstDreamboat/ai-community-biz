"""推送服务：企微/钉钉/通用 webhook 三类渠道真实下发。

- wecom：企业微信群机器人 webhook（POST msgtype=text）
- dingtalk：钉钉群机器人 webhook（POST msgtype=text，支持加签）
- webhook：通用 JSON webhook（POST 自定义 payload）

渠道地址通过环境变量/设置配置：
- PUSH_WECOM_WEBHOOK_URL
- PUSH_DINGTALK_WEBHOOK_URL
- PUSH_DINGTALK_SECRET（钉钉加签密钥，SEC 开头，可选；配置后自动计算签名）
- PUSH_WEBHOOK_URL
"""
import base64
import hashlib
import hmac
import logging
import time
from datetime import date, datetime
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opportunity import Opportunity, PushRecord

logger = logging.getLogger(__name__)

TIMEOUT = 10.0

SUPPORTED_CHANNELS = ("wecom", "dingtalk", "webhook")


def _dingtalk_webhook_url() -> str:
    """构建钉钉 webhook 地址；配置了加签密钥时自动附加 timestamp&sign 签名。"""
    url = settings.PUSH_DINGTALK_WEBHOOK_URL or ""
    if not url or not settings.PUSH_DINGTALK_SECRET:
        return url
    timestamp = str(round(time.time() * 1000))
    secret = settings.PUSH_DINGTALK_SECRET
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = quote(base64.b64encode(hmac_code).decode("utf-8"), safe="")
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}timestamp={timestamp}&sign={sign}"


def get_webhook_url(channel: str) -> str:
    """返回指定渠道的 webhook 地址（未配置返回空串）。钉钉含签名参数。"""
    if channel == "wecom":
        return settings.PUSH_WECOM_WEBHOOK_URL or ""
    if channel == "dingtalk":
        return _dingtalk_webhook_url()
    if channel == "webhook":
        return settings.PUSH_WEBHOOK_URL or ""
    return ""


def _render_content(record: PushRecord) -> str:
    """将推送记录渲染为可读文本。"""
    snap = record.content_snapshot or {}
    lines = [f"【AI存量项目商机挖掘】{snap.get('title') or '商机推荐'}"]
    if snap.get("province"):
        lines.append(f"区域：{snap['province']}")
    if snap.get("purchaser"):
        lines.append(f"采购方：{snap['purchaser']}")
    if snap.get("score") is not None:
        lines.append(f"评分：{snap['score']}（{snap.get('level') or ''}）")
    if snap.get("budget"):
        lines.append(f"预算：{snap['budget']}")
    if snap.get("recommend_reason"):
        lines.append(f"推荐理由：{snap['recommend_reason']}")
    return "\n".join(line for line in lines if line)


def send_push_record(db: Session, record: PushRecord) -> dict:
    """发送单条推送记录，更新其状态。返回发送结果。"""
    url = get_webhook_url(record.push_channel)
    if not url:
        record.status = "failed"
        record.error_msg = "渠道 webhook 地址未配置"
        db.commit()
        return {"ok": False, "error": record.error_msg}

    content = _render_content(record)
    try:
        if record.push_channel == "wecom":
            payload = {"msgtype": "text", "text": {"content": content}}
            resp = httpx.post(url, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            # 企微返回 {"errcode":0,"errmsg":"ok"}
            if body.get("errcode") not in (0, None):
                raise RuntimeError(f"企微返回错误: {body.get('errmsg') or body}")
        elif record.push_channel == "dingtalk":
            payload = {"msgtype": "text", "text": {"content": content}}
            resp = httpx.post(url, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            if body.get("errcode") not in (0, None):
                raise RuntimeError(f"钉钉返回错误: {body.get('errmsg') or body}")
        else:  # webhook 通用
            payload = {
                "type": "opportunity",
                "title": snap_title(record),
                "content": content,
                "sent_at": datetime.now().isoformat(timespec="seconds"),
            }
            resp = httpx.post(url, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
        record.status = "success"
        record.error_msg = None
        db.commit()
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        logger.warning("推送失败 record=%s channel=%s: %s", record.id, record.push_channel, e)
        record.status = "failed"
        record.error_msg = str(e)[:500]
        db.commit()
        return {"ok": False, "error": record.error_msg}


def snap_title(record: PushRecord) -> str:
    return (record.content_snapshot or {}).get("title") or f"商机-{record.opportunity_id}"


def send_pending_records(db: Session, channel: str | None = None, limit: int = 20) -> dict:
    """批量发送 pending 状态记录。返回统计。"""
    q = select(PushRecord).where(PushRecord.status == "pending")
    if channel:
        q = q.where(PushRecord.push_channel == channel)
    records = db.execute(q.order_by(PushRecord.id).limit(limit)).scalars().all()
    ok_n, fail_n = 0, 0
    for record in records:
        result = send_push_record(db, record)
        if result["ok"]:
            ok_n += 1
        else:
            fail_n += 1
    return {"total": len(records), "success": ok_n, "failed": fail_n}


def test_channel(channel: str, content: str = "AI存量项目商机挖掘系统 推送渠道连通性测试") -> dict:
    """测试指定渠道连通性。"""
    url = get_webhook_url(channel)
    if not url:
        raise ValueError(f"{channel} 渠道 webhook 地址未配置")
    try:
        if channel == "wecom":
            resp = httpx.post(url, json={"msgtype": "text", "text": {"content": content}}, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            if body.get("errcode") not in (0, None):
                raise RuntimeError(f"企微返回错误: {body.get('errmsg') or body}")
        elif channel == "dingtalk":
            resp = httpx.post(url, json={"msgtype": "text", "text": {"content": content}}, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            if body.get("errcode") not in (0, None):
                raise RuntimeError(f"钉钉返回错误: {body.get('errmsg') or body}")
        else:
            resp = httpx.post(
                url,
                json={"type": "test", "title": "渠道测试", "content": content},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def create_push_record(
    db: Session,
    opportunity_id: int,
    channel: str,
    receiver: str,
    push_date: date | None = None,
    auto_send: bool = True,
) -> PushRecord:
    """创建推送记录（同日同渠道同商机去重）。返回记录（可含发送后状态）。"""
    if channel not in SUPPORTED_CHANNELS:
        raise ValueError(f"不支持的推送渠道: {channel}")
    opp = db.execute(select(Opportunity).where(Opportunity.id == opportunity_id)).scalar_one_or_none()
    if opp is None:
        raise ValueError("商机不存在")

    today = push_date or date.today()
    exists = db.execute(
        select(PushRecord).where(
            PushRecord.opportunity_id == opportunity_id,
            PushRecord.push_channel == channel,
            PushRecord.push_date == today,
        )
    ).scalar_one_or_none()
    if exists:
        return exists

    from app.models.announcement import Announcement, ProjectProfile

    profile = (
        db.execute(select(ProjectProfile).where(ProjectProfile.id == opp.profile_id)).scalar_one_or_none()
        if opp.profile_id
        else None
    )
    ann = (
        db.execute(select(Announcement).where(Announcement.id == profile.announcement_id)).scalar_one_or_none()
        if profile
        else None
    )
    record = PushRecord(
        opportunity_id=opportunity_id,
        push_channel=channel,
        receiver=receiver,
        push_date=today,
        content_snapshot={
            "title": ann.title if ann else None,
            "province": profile.province if profile else None,
            "purchaser": profile.purchaser if profile else None,
            "budget": str(profile.budget) if profile and profile.budget else None,
            "score": str(opp.total_score or ""),
            "level": opp.level or "",
            "recommend_reason": opp.recommend_reason or "",
        },
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    if auto_send:
        send_push_record(db, record)
    return record
