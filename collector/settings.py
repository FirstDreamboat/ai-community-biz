"""Scrapy 采集服务配置（对应 ADD 5.1 / 开发规范第6节）。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# 并发与频率控制
CONCURRENT_REQUESTS = int(os.getenv("CRAWLER_CONCURRENCY", "8"))
DOWNLOAD_DELAY = float(os.getenv("CRAWLER_DOWNLOAD_DELAY", "1.0"))
ROBOTSTXT_OBEY = os.getenv("CRAWLER_ROBOTS", "true").lower() == "true"

# 重试
RETRY_TIMES = int(os.getenv("CRAWLER_RETRY_TIMES", "3"))
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# UA 轮换
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 数据库
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "opportunity")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "opportunity123")
MYSQL_DB = os.getenv("MYSQL_DB", "opportunity_system")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# 去重阈值
CONTENT_DEDUP_THRESHOLD = float(os.getenv("DEDUP_CONTENT_THRESHOLD", "0.85"))

# 代理池（可选）
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_POOL_URL = os.getenv("PROXY_POOL_URL", "")

# 采集关键词（全局默认，覆盖狄耐克主营：楼宇对讲/智能家居/智慧社区/医护对讲）
# 2026-08-21 全网罗扩充：弱电智能化全产业链关键词
DEFAULT_KEYWORDS = [
    # 基础业务
    "老旧小区改造", "城市更新", "智慧社区", "社区智能化", "小区智能化",
    # 狄耐克主营
    "楼宇对讲", "可视对讲", "对讲系统", "数字对讲", "IP对讲", "无线对讲",
    "门口机", "室内机", "呼叫系统", "智能家居", "智能面板", "智能网关",
    "医护对讲", "病房呼叫", "护士站", "医院智能化", "智慧医院", "医疗信息化",
    # 智能化工程
    "智能化工程", "弱电", "弱电工程", "综合布线", "系统集成",
    "楼宇自控", "信息发布", "广播系统", "会议系统", "能耗管理", "节能改造",
    # 安防监控
    "门禁", "安防", "监控", "视频监控", "周界防范", "报警系统", "电子围栏",
    "人脸识别", "车牌识别", "道闸", "停车场", "停车场管理",
    # 行业场景
    "智慧城市", "智慧园区", "智慧楼宇", "智慧医疗", "智慧养老", "医养结合", "康养",
    "物业管理", "物业服务", "校园广播", "电子班牌", "多媒体教室",
    # 通用
    "改造", "配套", "中标", "签约",
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
