"""APScheduler 定时任务：每日推荐推送、数据聚合、数据源定时采集。"""
import logging
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.opportunity import Opportunity
from app.models.sys import SysConfig

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _get_config(key: str) -> str | None:
    with SessionLocal() as db:
        row = db.execute(select(SysConfig).where(SysConfig.config_key == key)).scalar_one_or_none()
        return row.config_value if row else None


def push_daily_recommendation() -> None:
    """每日推送高评分商机推荐列表（走企微/钉钉/webhook 真实下发）。"""
    logger.info("执行每日商机推荐推送任务")
    from app.services import push_service

    # 推送渠道：按配置顺序选择可用渠道，全部未配置则仅落库
    channels = [
        ch for ch in ("wecom", "dingtalk", "webhook") if push_service.get_webhook_url(ch)
    ]
    if not channels:
        logger.warning("未配置任何推送 webhook 地址，仅落库推送记录")
        return

    with SessionLocal() as db:
        top_opps = (
            db.execute(
                select(Opportunity)
                .where(Opportunity.deleted == 0, Opportunity.level.in_(["high", "medium"]))
                .order_by(Opportunity.total_score.desc())
                .limit(50)
            )
            .scalars()
            .all()
        )
        for opp in top_opps:
            for channel in channels:
                push_service.create_push_record(
                    db,
                    opp.id,
                    channel,
                    receiver="daily-recommendation",
                    auto_send=True,
                )
        result = push_service.send_pending_records(db, limit=50)
    logger.info("每日推送任务完成，商机=%d 发送统计=%s", len(top_opps), result)


def build_daily_aggregation() -> None:
    """每日聚合驾驶舱统计。"""
    logger.info("执行每日聚合任务")
    from app.models.announcement import ProjectProfile

    with SessionLocal() as db:
        rows = (
            db.execute(
                select(Opportunity, ProjectProfile.province)
                .join(ProjectProfile, ProjectProfile.id == Opportunity.profile_id)
            )
            .all()
        )
        stat: dict[tuple, int] = {}
        for opp, province in rows:
            if province:
                key = ("region", province)
                stat[key] = stat.get(key, 0) + 1
            key = ("level", opp.level or "unknown")
            stat[key] = stat.get(key, 0) + 1
            key = ("status", opp.status)
            stat[key] = stat.get(key, 0) + 1
        logger.info("聚合完成，维度键数=%d", len(stat))


def _cron_field_match(field: str, value: int) -> bool:
    """匹配 cron 单字段（支持 *、数字、逗号列表）。"""
    if field == "*":
        return True
    for part in field.split(","):
        part = part.strip()
        if part == "*":
            return True
        if "/" in part:  # 简化：仅支持 */N 形式
            base, step = part.split("/", 1)
            if base in ("*", "0"):
                return value % int(step) == 0
        elif part.isdigit() and int(part) == value:
            return True
    return False


def cron_matches(cron_expr: str, now: datetime) -> bool:
    """判断 5 段 cron 表达式（分 时 日 月 周）是否匹配当前时间。"""
    try:
        minute, hour, day, month, weekday = cron_expr.split()
    except ValueError:
        return False
    # cron 周日=0，Python weekday 周一=0 → 偏移
    py_weekday = (now.weekday() + 1) % 7
    return (
        _cron_field_match(minute, now.minute)
        and _cron_field_match(hour, now.hour)
        and _cron_field_match(day, now.day)
        and _cron_field_match(month, now.month)
        and _cron_field_match(weekday, py_weekday)
    )


def run_scheduled_collect() -> None:
    """每分钟检查：命中数据源 schedule_cron 则触发合规采集。"""
    from app.models.data_source import DataSource
    from app.services import collector_service

    now = datetime.now()
    triggered = 0
    with SessionLocal() as db:
        sources = (
            db.execute(
                select(DataSource)
                .where(DataSource.status == 1, DataSource.deleted == 0)
                .where(DataSource.schedule_cron.isnot(None), DataSource.schedule_cron != "")
            )
            .scalars()
            .all()
        )
        for ds in sources:
            if cron_matches(ds.schedule_cron, now):
                try:
                    collector_service.trigger_collect(db, ds.id)
                    triggered += 1
                    logger.info("定时触发采集 source=%s cron=%s", ds.id, ds.schedule_cron)
                except Exception as e:  # noqa: BLE001
                    logger.exception("定时触发采集失败 source=%s: %s", ds.id, e)
    if triggered:
        logger.info("定时采集任务触发 %d 个数据源", triggered)


def run_scheduled_batch_parse() -> None:
    """定时批量解析未解析公告（解析 + AI 二次核验，防假商机）。

    兼容"采集完成后自动解析"：采集入库的公告会在下个周期自动被解析。
    若已有批量解析任务在跑则跳过本次。
    """
    from app.services import parse_service

    try:
        interval = int(_get_config("parse.interval_minutes") or "5")
        limit = int(_get_config("parse.batch_limit") or "30")
    except (TypeError, ValueError):
        interval, limit = 5, 30
    state = parse_service.start_batch_parse(limit=limit, reparse_failed=False, with_verify=True)
    if state is None:
        logger.info("定时批量解析：已有任务在运行，跳过本次")
        return
    logger.info("定时批量解析已启动，每 %d 分钟检查一次，limit=%d", interval, limit)


def start_scheduler() -> BackgroundScheduler:
    if scheduler.running:
        return scheduler
    daily_cron = _get_config("push.daily_cron") or "30 8 * * *"
    minute, hour, *_ = daily_cron.split()
    scheduler.add_job(push_daily_recommendation, "cron", hour=int(hour), minute=int(minute),
                      id="push_daily")
    scheduler.add_job(build_daily_aggregation, "cron", hour=2, minute=0, id="agg_daily")
    scheduler.add_job(run_scheduled_collect, "interval", minutes=1, id="collect_schedule")
    scheduler.add_job(run_scheduled_batch_parse, "interval", minutes=5, id="batch_parse_schedule")
    scheduler.start()
    logger.info("定时任务已启动: %s", daily_cron)
    return scheduler
