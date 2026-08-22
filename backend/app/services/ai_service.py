"""AI解析服务：DeepSeek 语义解析 + 模板规则兜底（对应 DLD 4）。"""
import json
import logging
import re
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import settings
from app.services import llm_quota
from app.services.verify_service import should_skip_llm

logger = logging.getLogger(__name__)

ANNOUNCEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "purchaser": {"type": ["string", "null"]},
        "project_type": {"type": ["string", "null"]},
        "budget_wanyuan": {"type": ["number", "null"]},
        "budget_est": {"type": "boolean"},
        "bid_deadline": {"type": ["string", "null"], "format": "date-time"},
        "open_time": {"type": ["string", "null"], "format": "date-time"},
        "qualification": {"type": "array", "items": {"type": "string"}},
        "tech_params": {"type": "array", "items": {"type": "string"}},
        "household_cnt": {"type": ["integer", "null"]},
        "building_cnt": {"type": ["integer", "null"]},
        "area_m2": {"type": ["number", "null"]},
        "contents": {
            "type": "array",
            "items": {
                "enum": ["对讲系统", "智能家居", "医护对讲", "门禁", "监控安防", "停车", "智能化工程", "照明", "供水", "绿化", "其他"]
            },
        },
        "fund_source": {"type": ["string", "null"]},
        "stage": {"type": ["string", "null"], "enum": ["规划", "招标", "施工", "其他"]},
        "relevance": {"type": ["string", "null"], "enum": ["高", "中", "低"]},
        "province": {"type": ["string", "null"]},
        "city": {"type": ["string", "null"]},
        "district": {"type": ["string", "null"]},
        "address": {"type": ["string", "null"]},
    },
    "required": ["contents", "budget_est", "stage"],
}

SYSTEM_PROMPT = """你是招标公告信息抽取专家。请从公告文本中抽取结构化信息，仅输出JSON对象，字段名必须与下面Schema完全一致，禁止使用其他字段名。

输出Schema（字段名、类型、枚举必须严格遵守）：
{
  "purchaser": "采购人名称，未提及为null",
  "project_type": "项目类型（如'老旧小区改造'），未知为null",
  "budget_wanyuan": "预算金额，单位万元，数字；未给出为null",
  "budget_est": "金额是否为估算值，布尔",
  "bid_deadline": "投标截止时间，ISO8601格式，无则null",
  "open_time": "开标时间，ISO8601格式，无则null",
  "qualification": "资质要求字符串数组，可为空数组",
  "tech_params": "技术参数/设备要求字符串数组，可为空数组",
  "household_cnt": "涉及户数，整数，未知为null",
  "building_cnt": "涉及楼栋数，整数，未知为null",
  "area_m2": "建筑面积，单位平方米，数字，未知为null",
  "contents": "改造内容标签数组，只能从['对讲系统','智能家居','医护对讲','门禁','监控安防','停车','智能化工程','照明','供水','绿化','其他']中选择",
  "fund_source": "资金来源（如'中央财政'），未知为null",
  "stage": "项目阶段，只能取'规划'|'招标'|'施工'|'其他'",
  "relevance": "与安防弱电行业相关度，取'高'|'中'|'低'",
  "province": "省份，未知为null",
  "city": "城市，未知为null",
  "district": "区县，未知为null",
  "address": "项目地址，未知为null"
}

规则：
1. 预算金额统一换算为万元；未给出金额输出null。
2. 未明确的信息输出null或空数组，禁止编造。
3. 时间输出ISO8601格式（如2026-09-30T09:00:00）。"""

# 模型可能输出的别名键 -> 标准键 兜底映射
KEY_ALIASES = {
    "project_name": "project_type",
    "procurement_agent": "purchaser",
    "procurement": "purchaser",
    "buyer": "purchaser",
    "budget_amount": "budget_wanyuan",
    "budget": "budget_wanyuan",
    "budget_is_estimated": "budget_est",
    "is_estimated": "budget_est",
    "bid_open_time": "bid_deadline",
    "deadline": "bid_deadline",
    "renovation_content": "contents",
    "renovation_items": "contents",
    "content_tags": "contents",
    "progress_stage": "stage",
    "funding_source": "fund_source",
    "area": "area_m2",
}


def _normalize_keys(result: dict) -> dict:
    """将模型返回的别名键归一化为标准键，并做基础类型修正。"""
    normalized = {k: v for k, v in result.items() if k not in KEY_ALIASES}
    for alias, standard in KEY_ALIASES.items():
        if alias in result and standard not in normalized:
            normalized[standard] = result[alias]
    # 布尔字符串 -> bool
    for key in ("budget_est",):
        if isinstance(normalized.get(key), str):
            normalized[key] = normalized[key].strip().lower() in ("true", "1", "是", "估算")
    return normalized


async def parse_with_deepseek(text: str) -> dict:
    """调用 DeepSeek 解析公告文本。失败抛出异常。"""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"公告文本：\n{text[:8000]}\n\n请输出JSON。"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 2000,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    llm_quota.record_usage()  # 成功调用一次，累加当日计数
    return _normalize_keys(json.loads(content))


def _clean_text(text: str) -> str:
    """清洗文本：去HTML标签、压缩空白。"""
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;|&amp;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_with_template(text: str) -> dict:
    """模板/规则兜底解析。"""
    t = _clean_text(text)
    result = {
        "purchaser": None,
        "project_type": None,
        "budget_wanyuan": None,
        "budget_est": True,
        "bid_deadline": None,
        "open_time": None,
        "qualification": [],
        "tech_params": [],
        "household_cnt": None,
        "building_cnt": None,
        "area_m2": None,
        "contents": [],
        "fund_source": None,
        "stage": None,
        "relevance": None,
        "province": None,
        "city": None,
        "district": None,
        "address": None,
    }

    # 预算：X万元 / X亿元
    m = re.search(r"预算[^0-9]{0,6}(\d+(?:\.\d+)?)\s*(亿|万)?元", t)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        result["budget_wanyuan"] = val * 10000 if unit == "亿" else val
        result["budget_est"] = False

    # 进度阶段
    for kw, stage in [("招标", "招标"), ("采购", "招标"), ("施工", "施工"),
                      ("规划", "规划"), ("公示", "招标"), ("成交", "其他")]:
        if kw in t:
            result["stage"] = stage
            break

    # 改造内容
    for kw, tag in [("楼宇对讲", "对讲系统"), ("可视对讲", "对讲系统"), ("对讲", "对讲系统"),
                    ("数字对讲", "对讲系统"), ("IP对讲", "对讲系统"), ("门口机", "对讲系统"), ("室内机", "对讲系统"),
                    ("智能家居", "智能家居"), ("智能面板", "智能家居"), ("智能网关", "智能家居"),
                    ("智能门锁", "智能家居"),
                    ("医护对讲", "医护对讲"), ("病房呼叫", "医护对讲"), ("护理呼叫", "医护对讲"),
                    ("医院", "医护对讲"), ("医疗", "医护对讲"), ("护士站", "医护对讲"),
                    ("门禁", "门禁"), ("人脸识别", "门禁"), ("安防", "监控安防"), ("监控", "监控安防"),
                    ("视频监控", "监控安防"), ("周界防范", "监控安防"), ("电子围栏", "监控安防"),
                    ("弱电", "智能化工程"), ("综合布线", "智能化工程"), ("系统集成", "智能化工程"),
                    ("智慧社区", "智能家居"), ("智慧园区", "智能家居"), ("智慧楼宇", "智能家居"),
                    ("停车", "停车"), ("道闸", "停车"), ("车牌识别", "停车"), ("停车场", "停车"),
                    ("照明", "照明"), ("供水", "供水"), ("绿化", "绿化"), ("节能改造", "智能化工程")]:
        if kw in t and tag not in result["contents"]:
            result["contents"].append(tag)

    # 资金性质
    if "中央财政" in t or "中央预算" in t:
        result["fund_source"] = "中央财政"
    elif "地方配套" in t or "地方财政" in t:
        result["fund_source"] = "地方配套"
    elif "自筹" in t:
        result["fund_source"] = "自筹"

    return result


def validate_result(result: dict) -> bool:
    """校验解析结果是否满足基本要求。"""
    if not isinstance(result, dict):
        return False
    return "contents" in result and isinstance(result.get("contents"), list)


async def parse_announcement(title: str, content: str) -> tuple[dict, str]:
    """解析公告，返回 (结构化结果, 解析来源)。

    消耗控制：
    - 本地预判与主营弱电智能化无关 且 标题无招标采购要素的公告直接模板解析，不调 LLM；
    - 每日限额用尽时解析降级为模板解析。
    """
    text = f"{title}\n{content or ''}"[:8000]
    if should_skip_llm(title, text):
        logger.info("本地预判无关公告，跳过LLM解析: %s", (title or "")[:50])
        return parse_with_template(text), "template"
    try:
        if not llm_quota.is_llm_available():
            logger.warning("DeepSeek 今日额度已用尽，解析降级为模板")
            return parse_with_template(text), "template"
        result = await parse_with_deepseek(text)
        source = "deepseek"
    except Exception as e:  # noqa: BLE001
        logger.warning("DeepSeek解析失败，走模板兜底: %s", e)
        result = parse_with_template(text)
        source = "template"

    if not validate_result(result):
        raise ValueError("解析结果不满足Schema要求")
    return result, source


def map_to_profile(result: dict, announcement_id: int) -> dict:
    """将解析结果映射为 project_profile 字段。"""
    return {
        "announcement_id": announcement_id,
        "purchaser": result.get("purchaser"),
        "project_type": result.get("project_type"),
        "budget": Decimal(str(result["budget_wanyuan"])) if result.get("budget_wanyuan") else None,
        "budget_est": 1 if result.get("budget_est") else 0,
        "bid_deadline": _parse_dt(result.get("bid_deadline")),
        "open_time": _parse_dt(result.get("open_time")),
        "qualification": result.get("qualification") or [],
        "tech_params": result.get("tech_params") or [],
        "household_cnt": result.get("household_cnt"),
        "building_cnt": result.get("building_cnt"),
        "area": Decimal(str(result["area_m2"])) if result.get("area_m2") else None,
        "contents": result.get("contents") or [],
        "fund_source": result.get("fund_source"),
        "stage": result.get("stage"),
        "relevance": result.get("relevance"),
        "province": result.get("province"),
        "city": result.get("city"),
        "district": result.get("district"),
        "address": result.get("address"),
    }


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None
