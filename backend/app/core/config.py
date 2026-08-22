"""应用配置：从环境变量加载。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/app/core/config.py -> 项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 应用
    APP_NAME: str = "AI存量项目商机挖掘系统"
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "*"

    # 数据库
    DATABASE_URL: str = (
        "mysql+pymysql://opportunity:opportunity123@127.0.0.1:3306/opportunity_system?charset=utf8mb4"
    )

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # 安全
    JWT_SECRET: str = "please-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # AI
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    EMBEDDING_MODEL: str = "deepseek-embedding"
    # DeepSeek 每日调用限额（<=0 表示不限）；超出后解析走模板、核验走本地规则，不再消耗额度
    DEEPSEEK_DAILY_LIMIT: int = 150

    # 内部接口触发令牌（供采集器采集完成后触发批量解析）
    INTERNAL_API_TOKEN: str = ""

    # 推送（企微/钉钉/通用 webhook 真实下发地址）
    PUSH_WEBHOOK_URL: str = ""
    PUSH_WECOM_WEBHOOK_URL: str = ""
    PUSH_DINGTALK_WEBHOOK_URL: str = ""
    # 钉钉机器人加签密钥（SEC 开头）。配置后发送时自动计算 timestamp&sign 签名
    PUSH_DINGTALK_SECRET: str = ""

    # 评分默认权重（对应 DBD sys_config scoring.weights）
    SCORING_WEIGHTS: dict = {"demand": 40, "budget": 20, "region": 15, "urgency": 15, "competition": 10}

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
