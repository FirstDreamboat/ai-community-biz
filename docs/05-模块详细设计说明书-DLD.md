# 模块详细设计说明书（DLD）
## AI存量项目商机挖掘系统

| 文档编号 | DLD-005 | 版本 | v1.0 |
|---------|--------|------|------|
| 编制日期 | 2026-08-21 | 编制人 | 研发组 |
| 依据文档 | SRS-001、ADD-002 | 评审状态 | 待评审 |

---

## 1. 总述

本文档按模块给出类设计、核心流程、算法逻辑与伪代码，开发按本设计落地。模块清单：

| 模块 | 服务 | 对应需求 |
|------|------|---------|
| 采集模块 | collector-service | FR-001~011 |
| AI解析模块 | ai-service | FR-012~016 |
| 智能匹配模块 | ai-service / decision-service | FR-017~023 |
| 推送跟进模块 | decision-service | FR-024~029 |
| 可视化模块 | web-console + api-gateway | FR-030~035 |
| 系统管理模块 | api-gateway | FR-036~039 |

---

## 2. 公共设计

### 2.1 公共数据结构

```python
# 公告统一标准对象
@dataclass
class Announcement:
    id: str                 # 去重指纹
    source_id: str          # 数据源ID
    source_url: str         # 原始URL
    title: str              # 标题
    content: str            # 正文（清洗后）
    publish_time: datetime  # 发布时间
    crawl_time: datetime    # 采集时间
    content_hash: str       # 内容MinHash指纹
    raw_html: str | None    # 原始HTML（备查）

# 项目画像对象
@dataclass
class ProjectProfile:
    announcement_id: str
    purchaser: str          # 招标方
    project_type: str       # 项目类型
    budget: Decimal | None  # 预算（万元）
    budget_est: bool        # 是否为估算
    deadlines: dict         # 时间节点 {投标截止, 开标, 报名截止}
    qualification: list[str]    # 资质要求
    tech_params: list[str]      # 技术参数
    scale: dict             # 规模 {户数, 楼栋数, 面积}
    contents: list[str]     # 改造内容标签
    fund_source: str        # 资金性质
    stage: str              # 进度阶段
    relevance: str          # 相关度 高/中/低
```

### 2.2 统一返回格式（API）

```json
{ "code": 0, "message": "ok", "data": { }, "trace_id": "..." }
```

### 2.3 日志与异常
- 统一 `logger` 封装，输出 JSON 结构化日志。
- 自定义异常体系：`BizError`（业务）、`ParseError`（解析）、`CrawlError`（采集）。

---

## 3. 采集模块详细设计

### 3.1 类设计

```
CollectorService
 ├─ BaseSpider (Scrapy.Spider)
 │    ├─ GovTenderSpider        中国政府采购网等政府招投标
 │    ├─ RegionalTenderSpider   省市公共资源交易中心
 │    ├─ PropertySpider         物业/城投公司动态
 │    ├─ PolicySpider           政策规划
 │    └─ NewsSpider             行业资讯展会
 ├─ SourceAdapter (API适配)
 ├─ DedupFilter                 URL + MinHash 双重去重
 ├─ Cleaner                     清洗（HTML去标签/编码归一/噪声过滤）
 └─ CollectorScheduler          定时调度
```

### 3.2 核心流程

```
定时触发/手动触发
  → 获取数据源配置（启停、频率、关键词、区域）
  → BaseSpider 发起请求（代理池+UA+频率控制）
  → 解析列表页 → 详情页 → 抽取字段
  → Cleaner 清洗
  → DedupFilter 去重（通过→入库入队；重复→丢弃计数）
  → 写入 announcement 表，投递消息队列（announcement.created）
  → 失败：重试≤3次 → 失败记录表 → 告警
```

### 3.3 关键算法：内容去重

```
输入: 新公告 content
1. url = normalize(new.url)   // 去除追踪参数
2. if url in redis.SET(url_index): return DUP
3. hash = minhash(content)     // 128位MinHash
4. if hash in redis.SET(content_index): return DUP
5. redis.SET 写入；返回 NEW
```

### 3.4 数据源配置模型

| 字段 | 类型 | 说明 |
|------|------|------|
| source_name | str | 数据源名称 |
| source_type | enum | gov/property/policy/news/api |
| base_url | str | 站点地址 |
| spider_class | str | 对应爬虫类 |
| keywords | list | 采集关键词 |
| regions | list | 区域范围 |
| schedule | str | cron 表达式 |
| enabled | bool | 启停 |
| proxy_enabled | bool | 是否走代理池 |

---

## 4. AI解析模块详细设计

### 4.1 类设计

```
AIService
 ├─ TextPreprocessor       去HTML、去噪、分块
 ├─ DeepSeekParser         DeepSeek 提示词解析引擎
 ├─ TemplateParser         模板/规则兜底解析
 ├─ ProfileGenerator       项目画像生成
 ├─ Vectorizer             Embedding 向量化
 └─ RagRetriever           RAG 检索
```

### 4.2 解析流程（伪代码）

```
def parse(announcement):
    text = TextPreprocessor.clean(announcement.content)
    result = DeepSeekParser.extract(text, schema=ANNOUNCEMENT_SCHEMA)
    if not validate(result):
        result = TemplateParser.extract(text)   # 兜底
    if not validate(result):
        mark_pending_human(announcement.id)     # 待人工
    profile = ProfileGenerator.generate(result, announcement)
    save_project_profile(profile)
    update_announcement_status(announcement.id, PARSED)
    emit("announcement.parsed", profile_id)
```

### 4.3 DeepSeek 提示词设计（要点）

```
系统提示：你是招标公告信息抽取专家，仅输出 JSON，字段遵循给定 Schema。
用户提示：<清洗后公告文本> + 字段要求：
  - 预算金额需归一化为万元并标记是否估算
  - 改造内容标签从字典中选择：对讲系统/门禁/监控安防/停车/照明/供水/绿化/其他
  - 进度阶段：规划/招标/施工/其他
  - 无明确信息字段输出 null，禁止编造
```

### 4.4 字段校验规则

| 字段 | 校验 |
|------|------|
| budget | 数值范围 0~10亿万元，超范围标记异常 |
| deadlines | ISO 时间格式，晚于公告发布时间 |
| scale | 户数/楼栋数 ≥ 0 整数 |
| contents | 必须命中标签字典 |
| relevance | 三选一 |

---

## 5. 智能匹配模块详细设计

### 5.1 三步式匹配

#### 第一轮：需求标签 ↔ 产品标签（粗匹配）
- 项目改造内容标签集 P = {p1,p2,...}
- 产品能力标签集 Q（知识库）
- 粗匹配得分 = |P ∩ Q| / |P|（Jaccard 相似度）

#### 第二轮：改造条件 ↔ 技术方案（深度语义匹配）
- 抽取项目约束条件（布线难、改造受限、老旧网络等）
- 与产品方案描述做向量余弦相似度
- 得分 = max(cos(cond_embed, solution_embed))

#### 第三轮：区域 ↔ 办事处覆盖
- 项目所在省市 ↔ 办事处/网点覆盖表匹配（v1.2：city 精确优先 → 省降级）
- 匹配优先序：省+市 cover(1.0) > 省+市 radiate(0.7) > 仅省 cover(0.8) > 仅省 radiate(0.53) > 无覆盖(0.3)
- 评分实现：`scoring_service.region_score`，办事处数据通过 `/offices` 接口维护

```
match_score = 0.3 * round1 + 0.5 * round2 + 0.2 * round3
```

### 5.2 商机评分引擎（伪代码）

```
def score(profile, knowledge, org):
    s1 = 40 * demand_match(profile, knowledge)          # 0-40
    s2 = budget_score(profile.budget)                   # 0-20
    s3 = 15 * region_match(profile.region, org.offices) # 0-15
    s4 = deadline_score(profile.deadlines)              # 0-15
    s5 = competitor_score(profile.competitors)          # 0-10
    total = round(s1+s2+s3+s4+s5, 1)
    return {total, {s1,s2,s3,s4,s5}, rules_version}
```

### 5.3 规则配置化
- 评分权重、分段阈值存 `scoring_rule` 表，版本化管理。
- 规则变更 → 生成新版本 → 支持按商机批量重算。

### 5.4 跟进策略生成

| 评分段 | 建议动作 | 话术模板 |
|--------|---------|---------|
| ≥70 | 立即联系、定制方案 | 首电模板/拜访模板 |
| 40-69 | 深入调研、标准方案 | 调研问卷模板 |
| <40 | 持续关注、定期复查 | 订阅提醒 |

---

## 6. 推送跟进模块详细设计

### 6.1 推送引擎
- 定时任务：每日 08:30 / 每周一 09:00 生成推荐列表。
- 渠道：站内消息（必发）+ 邮件/企微 Webhook（可配）。
- 幂等：推送记录表唯一约束（商机ID+渠道+日期）。

### 6.2 跟进状态机

```
新建 → 跟进中 → 已投标 → 已中标(✓)/已丢标(✗)
  ↑       │        │
  └───────┴────────┴──→ 无效/关闭
```
- 状态迁移记录存 `follow_up_log`。
- 逾期提醒：高评分商机 24h 未跟进 → 通知销售经理。

### 6.3 竞品监测
- 竞品关键词库：安居宝、立林等品牌 + 中标词。
- 解析公告命中 → 生成竞品中标记录 → 区域/产品分析。

---

## 7. 可视化模块详细设计

### 7.1 驾驶舱数据装配
```
GET /dashboard/overview
  → 聚合查询(总量/区域/评分/跟进状态) → Redis 缓存(5min) → 响应
```

### 7.2 热力图
- 前端 ECharts 地图 + 后端返回 `{province: count}` 数据。
- 下钻：省→市→区（同接口 region 参数）。

### 7.3 报表
- 月度趋势、区域热度、产品需求排行。
- 导出：后端生成 CSV/Excel 流式返回。

---

## 8. 系统管理模块详细设计
- RBAC：`user / role / permission / user_role` 表。
- 数据源管理：CRUD + 启停 + 调度配置（复用 3.4 模型）。
- 审计日志：登录、配置变更、规则变更、删除操作写审计表。
- 系统参数：键值表 `sys_config`。

---

## 9. 关键时序

### 9.1 采集→解析→评分→推送 全链路

```
Scheduler → Collector: crawl
Collector → MQ: announcement.created
AIWorker ← MQ: consume
AIWorker → DeepSeek: parse → save profile → MQ: announcement.parsed
ScoringWorker ← MQ: consume → compute score → save opportunity
PushScheduler (每日) → query top opportunities → push
Sales → API: follow-up → log
```

---

## 10. 智能商机挖掘模块详细设计（v1.1 新增）

### 10.1 存量项目生命周期推算（`intel_service.scan_legacy_projects_for_updates`）
```
年龄 = 当前年份 - install_year
年龄 > 10  → 超期：priority=高，action="IP两线换新"（推荐）
8-10 年    → 到期：priority=中，action="换新跟进"
6-8 年     → 临期：priority=低，action="提前布局"
< 6 年     → 服役期：不生成（skipped）
```
输出：新建/更新 `update_opportunity` 记录，可一键重跑幂等刷新。

### 10.2 销售线索四维评分（`intel_service.score_lead`）
```
score = 行业相关度(0-40) + 阶段(0-25) + 渠道(0-20) + 预算(0-15)
行业相关度：title/detail 命中 INDUSTRY_KEYWORDS 计分
阶段：初步接触 10 / 需求确认 18 / 方案报价 22 / 投标 25 / 已成交 25 / 已流失 0
渠道：全网招标 20 / 采购意向 18 / 改造计划 18 / 竞品中标 15 / 其他 8
预算：≥1000万 15 / 100-1000万 12 / <100万 6 / 未知 3
```

### 10.3 集采到期预警（`strategic_customer`）
- `contract_end_year - 当前年 ≤ 1` → 临期红标；`< 当前年` → 流失标记。
- 提供 `alerts` 接口供前端红黄牌展示。

### 10.4 竞品追踪生成（`generate_from_records`）
读取 `competitor_record` 中标记录 → 按竞品+城市聚合生成 `competitor_track`（后续标段/维保/续签类型）。

### 10.5 诉求热点聚合（`AppealHotspot`）
小区级聚合：投诉量、热度分（量级+时效加权）、痛点标签（JSON）、样本标题（JSON）、来源链接；`convert` 接口一键转正式商机。

### 10.6 数据模型
6 张新表（`LegacyProject/UpdateOpportunity/StrategicCustomer/SalesLead/CompetitorTrack/AppealHotspot`），字段见 DBD 3.15-3.20。

---

## 11. 安全设计（代码层）
- 所有 API 经 JWT 中间件鉴权；管理员接口校验角色。
- SQL 全部参数化（SQLAlchemy ORM），禁止拼接。
- DeepSeek 密钥、数据库密码走环境变量/密钥管理。
- 采集内容过滤 HTML/脚本标签（XSS 防护）。
- LLM 调用限额保护：`llm_quota` 计数持久化，超限自动降级，防额度超支。
