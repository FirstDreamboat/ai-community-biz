"""DeepSeek 每日调用限额：跨进程/重启持久化到文件。

用途：解析、核验等所有 LLM 调用前调用 is_llm_available() 判断是否放行；
每次成功调用后调用 record_usage() 累加计数。超出限额后系统自动降级
（解析走模板、核验走本地规则），避免额度超支。
"""
import json
import threading
from datetime import date
from pathlib import Path

from app.core.config import settings

_QUOTA_FILE = Path(__file__).resolve().parents[2] / ".llm_quota.json"
_lock = threading.Lock()


def _load() -> dict:
    try:
        data = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (FileNotFoundError, ValueError):
        pass
    return {"date": str(date.today()), "count": 0}


def _save(data: dict):
    _QUOTA_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def today_usage() -> int:
    """今日已用调用次数（按自然日）。"""
    data = _load()
    if data.get("date") != str(date.today()):
        return 0
    try:
        return int(data.get("count", 0))
    except (TypeError, ValueError):
        return 0


def record_usage(n: int = 1) -> int:
    """记录一次 LLM 调用，返回当日累计次数。"""
    with _lock:
        data = _load()
        today = str(date.today())
        if data.get("date") != today:
            data = {"date": today, "count": 0}
        data["count"] = int(data.get("count", 0)) + n
        _save(data)
        return data["count"]


def is_llm_available() -> bool:
    """是否还有可用额度（未配置限额视为不限）。"""
    limit = int(getattr(settings, "DEEPSEEK_DAILY_LIMIT", 0) or 0)
    if limit <= 0:
        return True
    return today_usage() < limit
