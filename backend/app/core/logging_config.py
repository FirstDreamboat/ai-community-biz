"""统一日志配置：JSON 结构化输出。"""
import json
import logging
import sys
import uuid
from datetime import datetime

from app.core.config import settings

_LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key in ("trace_id", "module", "extra"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(_LOG_LEVEL)


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]
