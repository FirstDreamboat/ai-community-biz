# API接口设计说明书（API）
## AI存量项目商机挖掘系统

| 文档编号 | API-004 | 版本 | v1.2 |
|---------|--------|------|------|
| 编制日期 | 2026-08-21（v1.2 更新 2026-08-22） | 编制人 | 研发组 |
| 依据文档 | SRS-001、ADD-002、DBD-003 | 评审状态 | 待评审 |

---

## 1. 接口规范总则

### 1.1 基础约定
- 协议：HTTPS；路径前缀：`/api/v1`
- 数据格式：JSON（UTF-8），日期时间 ISO8601
- 认证：`Authorization: Bearer <JWT>`
- 分页：`?page=1&page_size=20`，返回 `{ "total", "items" }`

### 1.2 统一返回结构

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "trace_id": "a1b2c3"
}
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40001 | 参数校验失败 |
| 40100 | 未认证/Token失效 |
| 40300 | 无权限 |
| 40400 | 资源不存在 |
| 50000 | 服务器内部错误 |
| 50300 | 上游服务（AI）不可用 |

### 1.3 公共错误示例

```json
{ "code": 40001, "message": "page 必须为正整数", "data": null, "trace_id": "x" }
```

---

## 2. 认证接口

### POST /api/v1/auth/login
登录获取 Token。
请求：
```json
{ "username": "sale01", "password": "******" }
```
响应：
```json
{ "code": 0, "data": { "token": "eyJ...", "expires_in": 86400, "user": { "id": 1, "username": "sale01", "real_name": "张三", "roles": ["sales"] } } }
```

### POST /api/v1/auth/logout
注销，使当前 Token 失效。请求体空。

### GET /api/v1/auth/me
获取当前用户信息与权限列表。
```json
{ "code": 0, "data": { "user": {...}, "permissions": ["opp:view","opp:follow"] } }
```

---

## 3. 商机模块接口

### 3.1 GET /api/v1/opportunities 商机列表（含筛选）

| 参数 | 类型 | 说明 |
|------|------|------|
| page / page_size | int | 分页 |
| keyword | string | 标题/招标方模糊搜索 |
| province / city | string | 区域筛选 |
| level | string | high/medium/low |
| status | string | new/following/bid/won/lost/closed |
| min_score / max_score | number | 评分范围 |
| relevance | string | high/medium/low |
| start_date / end_date | date | 公告时间范围 |
| sort | string | score_desc(默认)/publish_time_desc |

响应 data：
```json
{
  "total": 128,
  "page": 1,
  "page_size": 20,
  "items": [{
    "id": 1001,
    "title": "XX市2026年老旧小区改造项目招标公告",
    "province": "福建省", "city": "厦门市",
    "purchaser": "XX区住建局",
    "budget": 850.00,
    "contents": ["对讲系统","门禁","安防"],
    "stage": "招标",
    "total_score": 82.5,
    "level": "high",
    "status": "new",
    "publish_time": "2026-08-18T10:00:00"
  }]
}
```

### 3.2 GET /api/v1/opportunities/{id} 商机详情

| 参数 | 说明 |
|------|------|
| id | 商机ID |

返回包含：公告全文、项目画像、评分明细、跟进策略、跟进记录、竞品信息。

```json
{
  "code": 0,
  "data": {
    "opportunity": {...},
    "profile": {
      "purchaser": "...", "budget": 850, "bid_deadline": "2026-09-20T09:00:00",
      "household_cnt": 1200, "contents": ["对讲系统"], "fund_source": "中央财政+地方配套", "stage": "招标"
    },
    "score_detail": {
      "total": 82.5, "demand": 36, "budget": 16, "region": 15, "urgency": 10.5, "competition": 5, "rules_version": "v1"
    },
    "strategy": { "level": "high", "actions": ["立即联系招标方","准备定制化IP两线方案"] },
    "follow_logs": [],
    "competitors": []
  }
}
```

### 3.3 POST /api/v1/opportunities/{id}/follow-up 新增跟进记录

请求：
```json
{
  "action": "电话沟通",
  "to_status": "following",
  "note": "已确认项目含楼宇对讲需求，预算待核实",
  "next_plan": "周五前提供初步方案",
  "follow_time": "2026-08-21T14:30:00"
}
```
响应：`{ "code": 0, "data": { "id": 501, "to_status": "following" } }`
权限：`opp:follow`。状态非法流转返回 40001。

### 3.4 POST /api/v1/opportunities/{id}/assign 商机分配

请求：`{ "owner_id": 8 }`
权限：`opp:assign`（销售经理/管理员）。
响应：`{ "code": 0, "data": { "opportunity_id": 1001, "owner_id": 8 } }`

### 3.5 POST /api/v1/opportunities/{id}/recalc 商机重算评分

触发该商机重新评分（规则变更后使用）。
响应：`{ "code": 0, "data": { "new_score": 88.0 } }`

### 3.6 GET /api/v1/opportunities/export 商机导出

参数同列表接口，额外 `format=csv|xlsx`。响应为文件流（Content-Disposition 附件）。

---

## 4. 驾驶舱与报表接口

### 4.1 GET /api/v1/dashboard/overview 驾驶舱总览
```json
{
  "code": 0,
  "data": {
    "total_opportunities": 1280,
    "today_new": 64,
    "high_level_count": 210,
    "following_count": 320,
    "won_count": 18,
    "region_distribution": [ { "province": "福建", "count": 156 }, ... ],
    "score_distribution": [ { "range": "80-100", "count": 88 }, ... ],
    "status_funnel": [ { "status": "new", "count": 400 }, ... ]
  }
}
```

### 4.2 GET /api/v1/dashboard/heatmap 项目热力图数据

| 参数 | 说明 |
|------|------|
| level | province/city/district（下钻层级） |
| region | 上级区域编码（下钻时必填） |

```json
{ "code": 0, "data": { "items": [ { "region": "福建省", "count": 156 }, ... ] } }
```

### 4.3 GET /api/v1/dashboard/trends 趋势分析

| 参数 | 说明 |
|------|------|
| type | monthly（月度趋势）/region_hot（区域热度）/product_demand（产品需求排行） |
| start_date / end_date | 时间范围 |

```json
{ "code": 0, "data": { "items": [ { "month": "2026-07", "count": 95 }, ... ] } }
```

### 4.4 GET /api/v1/dashboard/trends/export 报表导出
参数同 4.3，`format=csv|xlsx`。

---

## 5. 公告与数据源接口

### 5.1 GET /api/v1/announcements 公告列表
参数：`source_id、parse_status、publish_time范围、keyword、分页`。
管理员与查看权限用户可读。

### 5.2 GET /api/v1/announcements/{id} 公告详情
含原始内容与解析结果。

### 5.3 POST /api/v1/announcements/{id}/re-parse 重新解析
触发重新解析（AI 或模板）。权限：`data:manage`。
响应：`{ "code": 0, "data": { "task_id": "t-100" } }`

### 5.4 GET /api/v1/data-sources 数据源列表
权限：`data:view`。返回数据源配置（含调度、启停状态）。

### 5.5 POST /api/v1/data-sources 新增数据源
权限：`data:manage`。
```json
{
  "source_name": "福建省公共资源交易中心",
  "source_type": "gov",
  "base_url": "https://...",
  "keywords": ["老旧小区改造","城市更新"],
  "regions": ["福建"],
  "schedule_cron": "0 8 * * *",
  "proxy_enabled": true
}
```

### 5.6 PUT /api/v1/data-sources/{id} 更新数据源
### 5.7 DELETE /api/v1/data-sources/{id} 删除（软删除）
### 5.8 POST /api/v1/data-sources/{id}/toggle 启停
### 5.9 POST /api/v1/data-sources/{id}/run 手动触发采集
响应：`{ "code": 0, "data": { "task_id": "c-200" } }`

### 5.10 GET /api/v1/collector-tasks 采集任务记录
参数：`source_id、status、分页`。

---

## 6. 产品知识库接口

### 6.1 GET /api/v1/knowledge 知识列表
参数：`category、keyword、分页`。

### 6.2 POST /api/v1/knowledge 新增知识
```json
{
  "title": "IP两线公寓对讲系统解决方案",
  "category": "对讲系统",
  "content": "...方案描述...",
  "tags": ["无需重铺线路","两线制","旧改适配"]
}
```
新增后自动异步重建向量。

### 6.3 PUT /api/v1/knowledge/{id} 更新知识
### 6.4 DELETE /api/v1/knowledge/{id} 停用知识
### 6.5 POST /api/v1/knowledge/reindex 重建向量索引

---

## 7. 竞品监测接口

### 7.1 GET /api/v1/competitors/records 竞品记录列表
参数：`competitor、province、result、分页`。

### 7.2 GET /api/v1/competitors/analysis 竞品分析
```json
{
  "code": 0,
  "data": {
    "by_region": [ { "competitor": "安居宝", "province": "广东", "count": 12 } ],
    "by_product": [ { "competitor": "立林", "category": "楼宇对讲", "count": 8 } ]
  }
}
```

### 7.3 竞品关键词管理
- `GET /api/v1/competitors/keywords`
- `PUT /api/v1/competitors/keywords`（更新关键词库，权限 `data:manage`）

---

## 8. 跟进看板接口

### 8.1 GET /api/v1/follow-ups 跟进记录查询
参数：`opportunity_id、user_id、date范围、action、分页`。

### 8.2 GET /api/v1/follow-ups/overdue 逾期提醒列表
返回超过 24h 未首次跟进的高评分商机。权限：`opp:view`（经理及以上）。

---

## 9. 系统管理接口

### 9.1 用户管理
- `GET /api/v1/users`（权限 sys:user:view）
- `POST /api/v1/users`（sys:user:manage）
- `PUT /api/v1/users/{id}`（sys:user:manage）
- `DELETE /api/v1/users/{id}`（软删除）

### 9.2 角色管理
- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PUT /api/v1/roles/{id}/permissions`（绑定权限）

### 9.3 系统配置
- `GET /api/v1/configs/{key}`（sys:config:view）
- `PUT /api/v1/configs/{key}`（sys:config:manage）
- 预置 key：`scoring.weights`、`push.channels`、`push.daily_cron`、`dedup.content_threshold`

### 9.4 审计日志
- `GET /api/v1/audit-logs`（sys:audit:view）参数：`user_id、module、date范围、分页`。

---

## 10. 系统健康

### GET /api/v1/health
```json
{ "code": 0, "data": { "status": "ok", "components": { "mysql": "up", "redis": "up", "ai_service": "up", "vector_db": "up" } } }
```

---

## 10.1 智能商机挖掘（v1.1 新增）

前缀：`/api/v1/intel`，统一响应 `{code, data, message}`。

### 10.1.1 存量项目台账
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/legacy-projects` | 台账分页查询（keyword/province/city/install_year/status） |
| POST | `/api/v1/intel/legacy-projects` | 新增台账 |
| PUT | `/api/v1/intel/legacy-projects/{id}` | 更新台账 |
| DELETE | `/api/v1/intel/legacy-projects/{id}` | 删除台账（软删） |

### 10.1.2 更新商机
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/update-opportunities` | 更新商机分页查询（priority/stage/status/action） |
| POST | `/api/v1/intel/update-opportunities/generate` | 一键扫描存量台账，按年限推算生成/刷新更新商机 |
| POST | `/api/v1/intel/update-opportunities/{id}/convert` | 转为正式商机 |
| PUT | `/api/v1/intel/update-opportunities/{id}` | 更新（调整阶段/状态） |
| DELETE | `/api/v1/intel/update-opportunities/{id}` | 删除 |

### 10.1.3 战略客户集采台账
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/strategic-customers` | 台账分页（keyword/type/expire_status） |
| POST | `/api/v1/intel/strategic-customers` | 新增 |
| PUT | `/api/v1/intel/strategic-customers/{id}` | 更新 |
| DELETE | `/api/v1/intel/strategic-customers/{id}` | 删除 |
| GET | `/api/v1/intel/strategic-customers/alerts` | 到期预警列表（≤1 年红标、已超期流失） |

### 10.1.4 销售线索
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/sales-leads` | 线索分页（keyword/province/city/channel/stage/status/score 排序） |
| POST | `/api/v1/intel/sales-leads` | 新增（自动四维评分） |
| PUT | `/api/v1/intel/sales-leads/{id}` | 更新（重新评分） |
| DELETE | `/api/v1/intel/sales-leads/{id}` | 删除 |
| POST | `/api/v1/intel/sales-leads/{id}/convert` | 转为正式商机 |

### 10.1.5 竞品后续追踪
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/competitor-tracks` | 追踪分页（competitor/status/city） |
| POST | `/api/v1/intel/competitor-tracks` | 新增 |
| POST | `/api/v1/intel/competitor-tracks/generate-from-records` | 从竞品中标记录一键生成追踪条目 |
| PUT | `/api/v1/intel/competitor-tracks/{id}` | 更新 |
| DELETE | `/api/v1/intel/competitor-tracks/{id}` | 删除 |

### 10.1.6 诉求热点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/appeal-hotspots` | 热点分页（keyword/city/status，按 hot_score 排序） |
| POST | `/api/v1/intel/appeal-hotspots` | 新增 |
| PUT | `/api/v1/intel/appeal-hotspots/{id}` | 更新 |
| DELETE | `/api/v1/intel/appeal-hotspots/{id}` | 删除 |
| POST | `/api/v1/intel/appeal-hotspots/{id}/convert` | 转为正式商机 |

### 10.1.7 统计
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/intel/stats/overview` | 汇总统计（各表数量、临期/超期/高热度聚合） |

---

## 11. 接口权限矩阵

| 接口 | admin | business_consultant | sales_manager | sales | viewer |
|------|:-----:|:-------------------:|:-------------:|:-----:|:------:|
| auth/* | √ | √ | √ | √ | √ |
| opportunities 查看 | √ | √ | √ | √ | √ |
| opportunities follow-up | √ | √ | √ | √ | × |
| opportunities assign | √ | × | √ | × | × |
| dashboard 查看 | √ | √ | √ | √ | √ |
| data-sources 管理 | √ | × | × | × | × |
| knowledge 管理 | √ | √ | × | × | × |
| competitors 查看 | √ | √ | √ | √ | √ |
| users/roles 管理 | √ | × | × | × | × |
| configs 管理 | √ | × | × | × | × |
| intel/* 查看 | √ | √ | √ | √ | √ |
| intel/* 管理 | √ | √ | √ | √ | × |
| intel/*/convert | √ | √ | √ | √ | × |

---

## 12. 版本与兼容性
- 接口版本通过路径 `/api/v1` 管理，破坏性变更升版。
- 新增字段向后兼容；删除字段需先弃用（deprecation）一版。
- OpenAPI 文档地址：`/docs`（Swagger UI，开发环境开放，生产环境需管理员）。

## 12.1 v1.2 新增接口（2026-08-22 落地）

### 12.1.1 推送真实下发（`/push`）
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/push/records` | 推送记录列表（按商机/渠道/状态过滤，分页） | 商机查看 |
| POST | `/api/v1/push/records` | 创建推送记录（同日同渠道同商机去重，可立即发送） | 商机跟进 |
| POST | `/api/v1/push/records/{id}/send` | 发送单条推送记录（企微/钉钉/通用 webhook） | 商机跟进 |
| POST | `/api/v1/push/records/send-pending` | 批量发送 pending 记录 | 商机跟进 |
| POST | `/api/v1/push/test` | 渠道连通性测试 | 商机跟进 |

渠道：`wecom`（企业微信群机器人）、`dingtalk`（钉钉群机器人）、`webhook`（通用 JSON）。
发送内容由 `content_snapshot`（标题/区域/采购方/预算/评分/理由）渲染。
地址配置：`PUSH_WECOM_WEBHOOK_URL` / `PUSH_DINGTALK_WEBHOOK_URL` / `PUSH_WEBHOOK_URL`（见 08 部署手册）。

### 12.1.2 办事处覆盖（`/offices`）
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/offices` | 办事处列表（省/市/关键词过滤） | 登录 |
| GET | `/api/v1/offices/match` | 区域覆盖匹配（city 精确优先→省降级） | 登录 |
| GET | `/api/v1/offices/coverage` | 覆盖概览（按省统计直营/辐射） | 登录 |
| POST | `/api/v1/offices` | 新增办事处 | 登录 |
| PUT | `/api/v1/offices/{id}` | 编辑办事处 | 登录 |
| DELETE | `/api/v1/offices/{id}` | 停用办事处 | 登录 |

### 12.1.3 政策信息库（`/knowledge/policies`）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge/policies` | 政策列表（级别/地区/关键词过滤，时间倒序） |
| POST | `/api/v1/knowledge/policies` | 新增政策 |
| PUT | `/api/v1/knowledge/policies/{id}` | 编辑政策 |
| DELETE | `/api/v1/knowledge/policies/{id}` | 删除政策 |

### 12.1.4 其他新增
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/opportunities/{id}/recalc` | 按最新规则重算商机评分（原 §13 缺口，已实现） |
| GET | `/api/v1/opportunities/export` | 按筛选条件导出商机 CSV（UTF-8 BOM，原 §13 缺口） |
| POST | `/api/v1/knowledge/reindex` | 知识库索引重建（文本指纹向量化，原 §13 缺口） |
| POST | `/api/v1/announcements/{id}/manual-fix` | 人工修正画像并重新生成商机（反馈闭环） |

## 13. 已闭环缺口（v1.2 核对）
> v1.1 待办缺口已全部落地，见《09-项目开发计划与里程碑.md》§9.1。

| 规划接口 | 文档出处 | 现状 |
|----------|----------|------|
| `POST /api/v1/opportunities/{id}/recalc`（重算评分） | 3.5 | ✅ v1.2 已实现 |
| `GET /api/v1/opportunities/export`（商机导出） | 3.6 | ✅ v1.2 已实现（CSV） |
| `POST /api/v1/knowledge/reindex`（向量索引重建） | 6.5 | ✅ v1.2 已实现（文本指纹） |
| `GET /api/v1/collector-tasks`（采集任务记录） | 5.10 | ⚠️ 路径为 `/data-sources/tasks`，未统一 |
| 推送渠道真实下发（webhook/企微/钉钉） | 12.1.1 | ✅ v1.2 已实现 |
| 政策信息库 `policy` 模块接口 | 12.1.3 | ✅ v1.2 已实现 |
