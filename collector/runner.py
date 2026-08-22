#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合规采集执行器（数据采集规范实现）。

用法:
    python runner.py --source <数据源ID> [--task <任务ID>] [--pages N]

合规要点（对齐《采集数据规范》）:
1. 采集前检查目标站点 robots.txt，禁止抓取则终止并记录失败原因；
2. User-Agent 明确标识采集身份（非伪装浏览器），便于站点联系；
3. 请求间隔 >= 3 秒（可通过系统配置 collector.request_interval 调整），
   超时、失败自动退避重试（最多 3 次）；
4. 仅抓取公开页面，不绕过验证码/登录/封禁/IP 限制，不做高频率并发；
5. 每条数据记录来源 URL 与原文快照，保证可追溯；
6. 以 URL 指纹做去重，重复内容不重复入库；
7. 采集数据仅用于内部商机分析，不外传。

依赖：仅 Python 标准库 + pymysql（backend 虚拟环境已安装）。
"""

import argparse
import hashlib
import json
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import urllib.request
from datetime import datetime

from pathlib import Path

import pymysql

# 项目根 / backend 目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
ENV_FILE = BACKEND_DIR / ".env"

# 兜底连接串：与 app/core/config.py 默认值保持一致，.env 缺失时仍可运行
DEFAULT_DATABASE_URL = (
    "mysql+pymysql://opportunity:opportunity123@127.0.0.1:3306/"
    "opportunity_system?charset=utf8mb4"
)

# 合规标识 UA（非伪装，纯 ASCII 以满足 HTTP 头编码要求）
USER_AGENT = (
    "AICommunity-Collector/1.0 "
    "(commercial-opportunity-analysis; contact: opp-admin@local; "
    "will stop crawling on request)"
)

DEFAULT_INTERVAL = 3.0     # 请求间隔（秒），合规下限 3s
DEFAULT_TIMEOUT = 15       # 单次请求超时（秒）
RETRY_TIMES = 3            # 失败重试次数
DEFAULT_MAX_PAGES = 20     # 列表页抓取上限
DEFAULT_MAX_DETAILS = 50   # 详情页抓取上限
MAX_RAW_HTML = 300_000     # 原文快照保存上限（字符）

_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

# 黄页/产品目录页特征词：命中即判定为非招标公告，跳过采集
# （注意：不包含"供应商"，避免误伤"供应商征集/资格预审"类真实商机公告）
_YELLOW_PAGE_KEYWORDS = [
    "价格", "报价", "厂家", "批发", "规格", "参数", "型号",
    "产品大全", "产品目录", "产品展示", "经销商", "多少钱",
    "哪家好", "排行榜", "热销", "促销", "招商加盟", "公司简介",
]

# 站点导航/门户链接特征词：命中即判定为导航页（首页/登录/平台入口等），非公告
_NAV_KEYWORDS = [
    "登录", "注册", "首页", "设为首页", "收藏本站", "平台入口", "系统入口",
    "监督平台", "交易平台首页", "帮助中心", "下载中心", "联系我们", "关于我们",
    "友情链接", "网站地图", "返回首页", "网站首页",
    "用户中心", "个人中心", "在线客服", "证书", "办事指南", "服务指南",
    "政策法规", "政策文件", "信息公开", "机构职能", "领导信箱", "互动交流",
    "无障碍", "旧版", "英文版", "移动端", "微信公众号", "二维码",
]

# 栏目聚合页特征：形如「智慧社区_智慧园区_智慧楼宇-智慧社区网」「XX网_XX网」，
# 「建设工程-无锡市公共资源交易中心」等栏目导航页；命中则跳过。
# 真实招标公告标题几乎不含「_」/「｜」，且不以「网/中心/平台」结尾，故不会误伤。
_COLUMN_PAGE_RE = re.compile(r"[_｜]")
_COLUMN_SUFFIX_RE = re.compile(
    r"-[^\s]{1,12}网$|_[^\s]{1,12}网$|_门户|_资讯|_频道"
    r"|-(?:[\u4e00-\u9fa5]{2,20}(?:交易中心|交易平台|政务服务中心|中心|平台|集团|公司|局|协会|委员会|管委会|厅|部|院|所))$"
)
# 站点功能页/栏目页（非公告）
_PORTAL_TITLE_KEYWORDS = [
    "开标大厅", "电子保函", "专家库", "交易系统", "信息库", "经营主体",
    "统一身份认证", "监管平台", "不见面开标", "报表",
    "培训系统", "信用信息", "主体信息", "政务动态", "年度工作报表",
    "回信", "调查征集", "建议咨询", "申请获取", "加载中", "公示信息",
    "能力评价", "企业入会", "企业服务中心", "会员动态", "协会要闻",
    "专家抽取", "不见面", "招标投标监管", "法规规章", "下载专区",
    "视频中心", "专题专栏", "政策解读", "数据开放", "数字证书",
]

# 供应商征集类公告特征词（真实商机，应入库并标记 category=solicit）
_SOLICIT_KEYWORDS = [
    "供应商征集", "征集供应商", "征集公告", "公开征集", "供应商入围",
    "供应商入库", "供应商名录", "供应商名单", "供应商库",
    "资格预审", "资格初审", "入围名单", "入库征集",
]


def is_column_page(anchor: str) -> bool:
    """判断锚文本是否为黄页站栏目聚合页或站点功能页（非招标公告）。"""
    if not anchor:
        return False
    if _COLUMN_SUFFIX_RE.search(anchor):
        return True
    if any(k in anchor for k in _PORTAL_TITLE_KEYWORDS):
        return True
    # 门户页标题：以「XX交易中心/交易平台/交易网/服务中心/政府采购网」结尾，
    # 且不含招标/采购/公告/磋商/询价等公告语义词 -> 判定为站点门户页
    if (anchor.endswith(("交易中心", "交易平台", "交易网", "交易系统",
                         "服务中心", "服务平台", "政府采购网", "服务网"))
            and not any(k in anchor for k in ("招标", "采购", "公告", "磋商",
                                              "询价", "比选", "项目", "工程"))):
        return True
    # 门户页标题带括号，如「全国公共资源交易平台（贵州省·贵阳市）」
    # （「交易平台」后跟括号区域名，不以平台/网结尾，需单独识别）
    if ("公共资源交易" in anchor
            and not any(k in anchor for k in ("招标", "采购", "公告", "磋商",
                                              "询价", "比选", "项目", "工程"))):
        return True
    # 行业门户站标题：含「门户网站/自媒体平台/行业资讯/新媒体」等特征词 -> 门户页
    if any(k in anchor for k in ("门户网站", "自媒体平台", "行业门户", "新媒体平台",
                                 "资讯平台", "新闻资讯、产品评测")):
        return True
    # 站点名开头 + 栏目导航，如「千家网_智慧城市_智能建筑」「千家照明网-专业照明行业门户」
    # （站点名以「网/号/站/平台」结尾后接 _ / - / ｜，多为栏目聚合页）
    if re.match(r"^[\u4e00-\u9fa5A-Za-z0-9]{1,20}(网|号|站|平台|在线)[_\-｜]", anchor):
        return True
    # 含「_」/「｜」且以「网」结尾，如「智慧商业_智能商业-智慧商业网」
    return bool(_COLUMN_PAGE_RE.search(anchor)) and anchor.rstrip().endswith("网")

_DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
    re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})"),
]

logger = logging.getLogger("collector.runner")

_last_req_time = [0.0]
_verify_ssl = True
_ssl_ctx = None  # verify_ssl=False 时的非校验上下文
_proxy_pool_url = ""  # 代理池地址（sys_config collector.proxy_pool_url）


def set_proxy_pool(url: str) -> None:
    """按 sys_config collector.proxy_pool_url 启用代理池（默认关闭）。

    合规说明：代理仅用于缓解单一出口的限流，仍遵守 robots.txt、
    请求间隔 >= 3s 与重试策略，不用于绕过封禁/验证码。
    """
    global _proxy_pool_url
    _proxy_pool_url = url or ""


def _get_proxy() -> str | None:
    """从代理池取一个代理地址；未配置代理池返回 None。"""
    if not _proxy_pool_url:
        return None
    try:
        req = urllib.request.Request(_proxy_pool_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            proxy = resp.read().decode("utf-8", "ignore").strip()
        return proxy if proxy.startswith(("http://", "https://", "socks")) else None
    except Exception as e:  # noqa: BLE001
        logger.warning("代理池获取失败: %s", e)
        return None


def set_verify_ssl(flag: bool) -> None:
    """按 sys_config collector.verify_ssl 开关 SSL 证书校验（默认开启）。"""
    global _verify_ssl, _ssl_ctx
    _verify_ssl = flag
    if flag:
        _ssl_ctx = None
        return
    _ssl_ctx = ssl._create_unverified_context()
    try:
        # 兼容部分政务站点仍使用旧式 TLS renegotiation
        _ssl_ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
    except Exception:  # noqa: BLE001
        pass


def _load_db_config() -> dict:
    """从 backend/.env 读取 DATABASE_URL 并解析连接参数；缺失时回退默认值。"""
    url = None
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        url = DEFAULT_DATABASE_URL
        logger.warning("未找到 DATABASE_URL（backend/.env），使用默认连接串")
    m = re.match(r"^[\w+]+://([^:]+):([^@]+)@([^:/]+):(\d+)/([^?]+)", url)
    if not m:
        sys.exit("无法解析 DATABASE_URL: " + url)
    return {
        "host": m.group(3),
        "port": int(m.group(4)),
        "user": urllib.parse.unquote(m.group(1)),
        "password": urllib.parse.unquote(m.group(2)),
        "database": urllib.parse.unquote(m.group(5)),
        "charset": "utf8mb4",
        "autocommit": True,
    }


def _read_env(key: str, default: str = "") -> str:
    """从 backend/.env 读取单个配置项。"""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default


def send_failure_alert(source_id: int, error: str) -> None:
    """采集失败告警：向已配置的推送渠道（企微/钉钉/通用 webhook）发送通知。"""
    content = (
        f"【AI存量项目商机挖掘-采集失败告警】\n"
        f"数据源ID：{source_id}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"错误：{str(error)[:400]}"
    )
    sent = False
    for key, url in (
        ("企微", _read_env("PUSH_WECOM_WEBHOOK_URL")),
        ("钉钉", _read_env("PUSH_DINGTALK_WEBHOOK_URL")),
        ("Webhook", _read_env("PUSH_WEBHOOK_URL")),
    ):
        if not url:
            continue
        try:
            payload = {"msgtype": "text", "text": {"content": content}} \
                if key in ("企微", "钉钉") else \
                {"type": "collect_alert", "title": "采集失败告警", "content": content}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            sent = True
        except Exception as e:  # noqa: BLE001
            logger.warning("采集失败告警发送失败(%s): %s", key, e)
    if not sent:
        logger.info("未配置推送渠道，采集失败告警仅落库（audit_log）")


def trigger_batch_parse(new_count: int, limit: int = 30) -> None:
    """采集完成后触发后端批量解析（解析 + AI 二次核验）。

    仅在有新增公告时触发；失败只告警，不影响采集结果。
    """
    if new_count <= 0:
        return
    base = _read_env("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
    token = _read_env("INTERNAL_API_TOKEN", "")
    if not token:
        logger.info("未配置 INTERNAL_API_TOKEN，跳过采集后批量解析触发")
        return
    url = base.rstrip("/") + "/announcements/batch-parse/trigger"
    body = json.dumps(
        {"limit": limit, "reparse_failed": False, "with_verify": True},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-Internal-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        logger.info("已触发后端批量解析（新增 %d 条）", new_count)
    except Exception as e:  # noqa: BLE001
        logger.warning("触发批量解析失败（不影响采集结果）: %s", e)


def _get_config_int(db, key: str, default: int) -> int:
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT config_value FROM sys_config WHERE config_key=%s", (key,)
            )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] else default
    except Exception:  # noqa: BLE001
        return default


def _get_config_str(db, key: str, default: str = "") -> str:
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT config_value FROM sys_config WHERE config_key=%s", (key,)
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else default
    except Exception:  # noqa: BLE001
        return default


def _check_robots(base_url: str, ua: str) -> None:
    """robots.txt 合规检查。文件不可达时按 best-effort 允许。"""
    robots_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", "ignore")
            rp.parse(body.splitlines())
    except Exception:  # noqa: BLE001
        logger.info("robots.txt 不可达(%s)，按允许处理", robots_url)
        return
    if not rp.can_fetch(ua, base_url):
        raise RuntimeError(f"目标站点 robots.txt 禁止抓取：{robots_url}")


def _decode(raw: bytes, resp) -> str:
    charset = resp.headers.get_content_charset()
    if charset:
        try:
            return raw.decode(charset, "ignore")
        except LookupError:
            pass
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def fetch(url: str, interval: float = DEFAULT_INTERVAL,
          timeout: int = DEFAULT_TIMEOUT, use_proxy: bool = False) -> tuple[str, str]:
    """限速 + 重试的合规请求。返回 (html文本, 最终URL)。

    use_proxy=True 且已配置代理池时，通过代理池出口请求
    （合规：仍遵守 robots/限速/重试，不用于绕过封禁验证码）。
    """
    last_err = None
    proxy = _get_proxy() if use_proxy else None
    opener = None
    if proxy:
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("代理构建失败，退回直连: %s", e)
            opener = None
    for attempt in range(RETRY_TIMES):
        wait = interval - (time.time() - _last_req_time[0])
        if wait > 0:
            time.sleep(wait)
        _last_req_time[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        kwargs = {} if _verify_ssl else {"context": _ssl_ctx}
        try:
            if opener is not None:
                with opener.open(req, timeout=timeout) as resp:
                    raw = resp.read()
                    return _decode(raw, resp), resp.geturl()
            with urllib.request.urlopen(req, timeout=timeout, **kwargs) as resp:
                raw = resp.read()
                return _decode(raw, resp), resp.geturl()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            logger.warning("请求失败(url=%s, attempt=%s): %s", url, attempt + 1, e)
            if attempt < RETRY_TIMES - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"请求失败（重试{RETRY_TIMES}次）：{last_err}")


def strip_tags(text: str) -> str:
    text = _SCRIPT_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(html_text: str, fallback: str) -> str:
    m = _TITLE_RE.search(html_text)
    title = strip_tags(m.group(1)) if m else ""
    if not title:
        title = fallback
    # 剥离站点名尾巴，如「_全国公共资源交易平台（安徽省·合肥市）」「-某某交易网」
    for sep in ("_", "－", "—", "-"):
        if sep in title:
            head, _, tail = title.rpartition(sep)
            if head and (tail.startswith("全国") or "公共资源" in tail or tail.endswith("网")
                         or tail.endswith("中心") or tail.endswith("平台")):
                title = head
    return title.strip()[:500]


def extract_content(html_text: str) -> str:
    """提取正文纯文本（去脚本/样式/标签）。"""
    text = strip_tags(html_text)
    return text[:20000]


def extract_publish_time(html_text: str) -> datetime | None:
    for pat in _DATE_PATTERNS:
        m = pat.search(html_text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def extract_links(html_text: str, base_url: str) -> list[tuple[str, str]]:
    links = []
    for href, text in _LINK_RE.findall(html_text):
        anchor = strip_tags(text)
        if not anchor:
            continue
        url = urllib.parse.urljoin(base_url, href)
        if not url.startswith(("http://", "https://")):
            continue
        links.append((url, anchor))
    return links


def fingerprint(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


_PAGE_PARAM_NAMES = ("page", "p", "pageNum", "pageIndex", "pageNo")


def next_page_url(url: str, page: int) -> str | None:
    """对列表页 URL 追加/替换分页参数；page<=1 返回原 URL。"""
    if page <= 1:
        return url
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    for name in _PAGE_PARAM_NAMES:
        if any(k == name for k, _ in query):
            query = [(name, str(page)) if k == name else (k, v) for k, v in query]
            break
    else:
        query.append(("page", str(page)))
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(query),
            parsed.fragment,
        )
    )


def collect_list_links(db, entries: list[str], keywords: list[str],
                       interval: float, max_pages: int,
                       use_proxy: bool = False) -> list[tuple[str, str]]:
    """多入口 + 自动翻页抓取列表页候选链接，按关键词过滤、URL 去重。

    每个入口最多翻 max_pages 页；连续 2 页无新增链接则提前停止。
    """
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        for page in range(1, max_pages + 1):
            page_url = next_page_url(entry, page)
            try:
                page_html, _ = fetch(page_url, interval=interval, use_proxy=use_proxy)
            except Exception as e:  # noqa: BLE001
                logger.warning("列表页抓取失败 %s: %s", page_url, e)
                break
            before = len(candidates)
            for url, anchor in extract_links(page_html, page_url):
                if keywords and not any(k in anchor or k in url for k in keywords):
                    continue
                # 过滤黄页/产品目录页（如「XX价格|型号|厂家」），非招标公告
                if any(k in anchor for k in _YELLOW_PAGE_KEYWORDS):
                    continue
                # 过滤站点导航/门户链接（登录/首页/平台入口等）
                if any(k in anchor for k in _NAV_KEYWORDS):
                    continue
                # 过滤栏目聚合页（如「智慧社区_智慧园区_智慧楼宇-智慧社区网」）
                if is_column_page(anchor):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                candidates.append((url, anchor))
                if len(candidates) >= DEFAULT_MAX_DETAILS:
                    return candidates
            if page > 1 and len(candidates) == before:
                break  # 本页无新增，停止翻页
        if len(candidates) >= DEFAULT_MAX_DETAILS:
            break
    return candidates


def exists_announcement(db, fp: str) -> bool:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM announcement WHERE fingerprint=%s AND deleted=0 LIMIT 1",
            (fp,),
        )
        return cur.fetchone() is not None


def insert_announcement(db, ds, url: str, final_url: str, title: str,
                        content: str, raw_html: str, pub_time, category: str) -> None:
    fp = fingerprint(url)
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO announcement
               (fingerprint, source_id, source_url, title, content, raw_html,
                publish_time, crawl_time, parse_status, category, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),0,%s,NOW(),NOW())""",
            (fp, ds["id"], url, title, content, raw_html[:MAX_RAW_HTML], pub_time, category),
        )


def update_task(db, task_id, status, new_count=0, dup_count=0,
                fail_count=0, error_msg=None, finished=True):
    if task_id is None:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db.cursor() as cur:
        cur.execute(
            """UPDATE collector_task_log SET status=%s, new_count=%s, dup_count=%s,
               fail_count=%s, error_msg=%s, finished_at=%s WHERE id=%s""",
            (status, new_count, dup_count, fail_count, error_msg, now if finished else None, task_id),
        )


def update_source(db, source_id, run_status, error_msg=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db.cursor() as cur:
        cur.execute(
            "UPDATE data_source SET last_run_at=%s, last_run_status=%s WHERE id=%s",
            (now, run_status, source_id),
        )
        if error_msg:
            cur.execute(
                """INSERT INTO audit_log (user_id, action, module, target_id, detail, ip, created_at)
                   VALUES (NULL,'collect_failed','collector',%s,%s,NULL,NOW())""",
                (str(source_id), json.dumps({"error": str(error_msg)[:500]}, ensure_ascii=False)),
            )
    if error_msg:
        # 采集失败即时告警（企微/钉钉/webhook，仅当渠道已配置时下发）
        send_failure_alert(source_id, error_msg)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="合规采集执行器")
    parser.add_argument("--source", type=int, required=True, help="数据源 ID")
    parser.add_argument("--task", type=int, default=None, help="采集任务记录 ID")
    parser.add_argument("--pages", type=int, default=DEFAULT_MAX_PAGES, help="列表页数量上限")
    args = parser.parse_args()

    db = pymysql.connect(**_load_db_config())
    new_count = dup_count = fail_count = 0
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, source_name, source_type, base_url, keywords, regions, "
                "status, proxy_enabled, list_pages FROM data_source "
                "WHERE id=%s AND deleted=0",
                (args.source,),
            )
            row = cur.fetchone()
        if not row:
            update_task(db, args.task, "failed", error_msg="数据源不存在")
            return 1
        ds_id, ds_name, ds_type, base_url, keywords, regions, status, proxy, list_pages = row
        if status != 1:
            update_task(db, args.task, "failed", error_msg="数据源已停用")
            return 1
        keywords = keywords or []
        regions = regions or []
        if not base_url or not base_url.startswith(("http://", "https://")):
            update_task(db, args.task, "failed", error_msg="数据源缺少合法 base_url")
            return 1

        interval = _get_config_int(db, "collector.request_interval", int(DEFAULT_INTERVAL))
        interval = max(interval, 3)  # 合规下限 3 秒
        max_pages = min(args.pages, DEFAULT_MAX_PAGES)
        set_verify_ssl(_get_config_int(db, "collector.verify_ssl", 1) != 0)
        # 代理池（可选）：sys_config collector.proxy_pool_url；数据源 proxy_enabled=1 时启用
        proxy_pool = _get_config_str(db, "collector.proxy_pool_url", "")
        set_proxy_pool(proxy_pool)
        use_proxy = bool(proxy and proxy_pool)

        logger.info("开始采集 source=%s name=%s url=%s", ds_id, ds_name, base_url)
        _check_robots(base_url, USER_AGENT)

        # 1) 多入口 + 翻页抓取列表页，提取候选链接并按关键词过滤
        entries = (list_pages if isinstance(list_pages, list) and list_pages
                   else [base_url])
        entries = [e for e in entries if isinstance(e, str) and e.startswith("http")]
        if not entries:
            entries = [base_url]
        candidates = collect_list_links(db, entries, keywords, interval, max_pages, use_proxy)
        logger.info(
            "入口页 %d 个，关键词过滤后候选链接 %d 条",
            len(entries), len(candidates),
        )

        category = "tender" if ds_type in ("gov", "trade") else ds_type or "news"

        # 2) 去重 + 抓详情 + 入库
        for url, anchor in candidates:
            fp = fingerprint(url)
            if exists_announcement(db, fp):
                dup_count += 1
                continue
            try:
                detail_html, final_url = fetch(url, interval=interval, use_proxy=use_proxy)
                title = extract_title(detail_html, anchor)
                content = extract_content(detail_html)
                # 二次过滤：标题仍为黄页/导航/栏目特征、标题==源名、或正文过短（疑似列表页/空页），跳过
                if (any(k in title for k in _YELLOW_PAGE_KEYWORDS)
                        or any(k in title for k in _NAV_KEYWORDS)
                        or is_column_page(title)
                        or title == ds_name
                        or len(title.strip()) < 6
                        or len(content) < 80):
                    dup_count += 1
                    logger.info("跳过非公告页 %s | %s", title[:60], url)
                    continue
                pub_time = extract_publish_time(detail_html)
                # 供应商征集/资格预审类公告单独标记（category=solicit，真实商机）
                if any(k in title for k in _SOLICIT_KEYWORDS):
                    item_category = "solicit"
                else:
                    item_category = category
                insert_announcement(
                    db, {"id": ds_id}, url, final_url, title, content,
                    detail_html, pub_time, item_category,
                )
                new_count += 1
                logger.info("入库[%s] %s | %s", item_category, title[:60], url)
            except Exception as e:  # noqa: BLE001
                fail_count += 1
                logger.warning("详情抓取失败 %s: %s", url, e)

        update_task(db, args.task, "success", new_count, dup_count, fail_count)
        update_source(db, ds_id, "success")
        logger.info("采集完成：新增=%d 去重=%d 失败=%d", new_count, dup_count, fail_count)
        # 采集完成自动触发批量解析（解析 + AI 二次核验，防假商机）
        trigger_batch_parse(new_count)
        return 0
    except Exception as e:  # noqa: BLE001
        logger.exception("采集任务异常")
        update_task(db, args.task, "failed", new_count, dup_count, fail_count, str(e)[:500])
        update_source(db, args.source, "failed", str(e)[:500])
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
