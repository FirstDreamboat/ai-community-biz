# 数据库设计说明书（DBD）
## AI存量项目商机挖掘系统

| 文档编号 | DBD-003 | 版本 | v1.0 |
|---------|--------|------|------|
| 编制日期 | 2026-08-21 | 编制人 | 研发组/DBA |
| 依据文档 | SRS-001、ADD-002 | 评审状态 | 待评审 |

---

## 1. 设计总览

### 1.1 数据库选型
| 存储 | 用途 | 说明 |
|------|------|------|
| MySQL 8.0 | 业务主数据 | InnoDB，utf8mb4 |
| Redis | 缓存/队列/去重 | Bloom Filter 去重、热点缓存 |
| 向量库（pgvector/Chroma） | 产品知识库向量 | 语义检索 |
| 文件存储 | 公告原始HTML、导出文件 | 对象存储/本地磁盘 |

### 1.2 命名规范
- 表名：小写下划线，业务前缀（`ann_` 公告、`opp_` 商机、`sys_` 系统）。
- 主键：`id BIGINT UNSIGNED AUTO_INCREMENT`。
- 通用字段：`created_at`、`updated_at`、`deleted`（软删除标志 0/1）。
- 索引命名：`idx_字段`，唯一索引 `uk_字段`。

---

## 2. ER 关系总览

```
data_source 1─n announcement 1─1 project_profile
                             1─n opportunity 1─n score_detail
                                           1─n follow_up_log
                                           1─n push_record
announcement 1─n competitor_record
sys_user 1─n follow_up_log
sys_user n─n sys_role（user_role）
sys_role n─n sys_permission（role_permission）
product_knowledge（知识库）→ vector（向量库）
policy_info（政策库）n─m announcement
```

---

## 3. 表结构详细设计

### 3.1 数据源表 `data_source`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| source_name | VARCHAR(100) | NOT NULL | 数据源名称 |
| source_type | VARCHAR(20) | NOT NULL | gov/property/policy/news/api |
| base_url | VARCHAR(500) | NULL | 站点地址 |
| spider_class | VARCHAR(100) | NULL | 爬虫类名 |
| keywords | JSON | NULL | 采集关键词 |
| regions | JSON | NULL | 区域范围 |
| schedule_cron | VARCHAR(50) | NULL | 调度cron |
| proxy_enabled | TINYINT(1) | DEFAULT 0 | 是否代理 |
| status | TINYINT(1) | DEFAULT 1 | 1启用 0停用 |
| last_run_at | DATETIME | NULL | 最近运行时间 |
| last_run_status | VARCHAR(20) | NULL | success/failed/running |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`uk_source_name(source_name, deleted)`、`idx_source_type(source_type)`

### 3.2 公告表 `announcement`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| fingerprint | VARCHAR(64) | UNIQUE | 去重指纹（url hash + minhash） |
| source_id | BIGINT UNSIGNED | NOT NULL, FK | 数据源ID |
| source_url | VARCHAR(1000) | NULL | 原始URL |
| title | VARCHAR(500) | NOT NULL | 标题 |
| content | LONGTEXT | NULL | 正文（清洗后） |
| raw_html | LONGTEXT | NULL | 原始HTML |
| publish_time | DATETIME | NULL | 发布时间 |
| crawl_time | DATETIME | NOT NULL | 采集时间 |
| parse_status | TINYINT | DEFAULT 0 | 0待解析 1已解析 2解析失败 3待人工 |
| category | VARCHAR(20) | NULL | tender/property/policy/news |
| extra | JSON | NULL | 扩展信息 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_source_id(source_id)`、`idx_publish_time(publish_time)`、`idx_parse_status(parse_status)`、`uk_fingerprint(fingerprint)`

### 3.3 项目画像表 `project_profile`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| announcement_id | BIGINT UNSIGNED | FK, UNIQUE | 公告ID |
| purchaser | VARCHAR(200) | NULL | 招标方 |
| project_type | VARCHAR(50) | NULL | 项目类型 |
| budget | DECIMAL(14,2) | NULL | 预算金额（万元） |
| budget_est | TINYINT(1) | DEFAULT 0 | 是否估算 |
| bid_deadline | DATETIME | NULL | 投标截止 |
| open_time | DATETIME | NULL | 开标时间 |
| qualification | JSON | NULL | 资质要求 |
| tech_params | JSON | NULL | 技术参数 |
| household_cnt | INT | NULL | 户数 |
| building_cnt | INT | NULL | 楼栋数 |
| area | DECIMAL(12,2) | NULL | 建筑面积(㎡) |
| contents | JSON | NULL | 改造内容标签 |
| fund_source | VARCHAR(20) | NULL | 资金性质 |
| stage | VARCHAR(20) | NULL | 进度阶段 |
| relevance | VARCHAR(10) | NULL | 高/中/低 |
| province | VARCHAR(50) | NULL | 省 |
| city | VARCHAR(50) | NULL | 市 |
| district | VARCHAR(50) | NULL | 区县 |
| address | VARCHAR(300) | NULL | 地址 |
| parsed_by | VARCHAR(50) | NULL | deepseek/template/human |
| human_verified | TINYINT(1) | DEFAULT 0 | 人工确认 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_province(province)`、`idx_budget(budget)`、`idx_stage(stage)`、`idx_relevance(relevance)`

### 3.4 商机表 `opportunity`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| profile_id | BIGINT UNSIGNED | FK, UNIQUE | 项目画像ID |
| total_score | DECIMAL(5,1) | NOT NULL | 综合评分 |
| demand_score | DECIMAL(4,1) | NULL | 需求匹配度(40) |
| budget_score | DECIMAL(4,1) | NULL | 预算规模(20) |
| region_score | DECIMAL(4,1) | NULL | 区域覆盖(15) |
| urgency_score | DECIMAL(4,1) | NULL | 时间紧迫度(15) |
| competition_score | DECIMAL(4,1) | NULL | 竞争态势(10) |
| rules_version | VARCHAR(20) | NOT NULL | 评分规则版本 |
| level | VARCHAR(10) | NULL | 高/中/低评分段 |
| status | VARCHAR(20) | DEFAULT 'new' | new/following/bid/won/lost/closed |
| owner_id | BIGINT UNSIGNED | NULL, FK | 负责销售 |
| assign_time | DATETIME | NULL | 分配时间 |
| recommend_reason | TEXT | NULL | 推荐理由 |
| follow_strategy | JSON | NULL | 跟进策略 |
| score_at | DATETIME | NOT NULL | 评分时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_status(status)`、`idx_level(level)`、`idx_owner(owner_id)`、`idx_score(total_score)`、`idx_score_at(score_at)`

### 3.5 跟进记录表 `follow_up_log`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| opportunity_id | BIGINT UNSIGNED | FK | 商机ID |
| user_id | BIGINT UNSIGNED | FK | 操作人 |
| action | VARCHAR(50) | NOT NULL | 动作（电话/拜访/投标/中标/丢标等） |
| from_status | VARCHAR(20) | NULL | 原状态 |
| to_status | VARCHAR(20) | NULL | 新状态 |
| note | TEXT | NULL | 跟进说明 |
| next_plan | VARCHAR(500) | NULL | 下一步计划 |
| follow_time | DATETIME | NOT NULL | 跟进时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |

索引：`idx_opportunity(opportunity_id)`、`idx_user(user_id)`、`idx_follow_time(follow_time)`

### 3.6 推送记录表 `push_record`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| opportunity_id | BIGINT UNSIGNED | FK | 商机ID |
| push_channel | VARCHAR(20) | NOT NULL | sms/email/webhook |
| receiver | VARCHAR(200) | NOT NULL | 接收人 |
| push_date | DATE | NOT NULL | 推送日期 |
| content_snapshot | JSON | NULL | 推送内容快照 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/success/failed |
| error_msg | VARCHAR(500) | NULL | 失败原因 |
| created_at | DATETIME | NOT NULL | 创建时间 |

索引：`uk_opp_channel_date(opportunity_id, push_channel, push_date)`、`idx_status(status)`

### 3.7 竞品监测表 `competitor_record`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| competitor | VARCHAR(50) | NOT NULL | 竞品名称 |
| announcement_id | BIGINT UNSIGNED | FK | 来源公告 |
| profile_id | BIGINT UNSIGNED | NULL | 关联画像 |
| province | VARCHAR(50) | NULL | 省份 |
| result | VARCHAR(20) | NULL | 中标/投标 |
| amount | DECIMAL(14,2) | NULL | 金额（万元） |
| detected_at | DATETIME | NOT NULL | 发现时间 |
| created_at | DATETIME | NOT NULL | 创建时间 |

索引：`idx_competitor(competitor)`、`idx_province(province)`

### 3.8 产品知识库表 `product_knowledge`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| title | VARCHAR(200) | NOT NULL | 知识标题 |
| category | VARCHAR(50) | NOT NULL | 分类（对讲/门禁/停车/社区等） |
| content | TEXT | NOT NULL | 内容/方案描述 |
| tags | JSON | NULL | 能力标签 |
| vector_id | VARCHAR(64) | NULL | 向量库ID |
| status | TINYINT(1) | DEFAULT 1 | 1启用 0停用 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

索引：`idx_category(category)`

### 3.9 政策信息表 `policy_info`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| title | VARCHAR(500) | NOT NULL | 政策标题 |
| level | VARCHAR(20) | NULL | 国家级/省级/市级 |
| region | VARCHAR(100) | NULL | 发布地区 |
| content | TEXT | NULL | 政策内容 |
| publish_time | DATETIME | NULL | 发布日期 |
| announcement_ids | JSON | NULL | 关联公告ID |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

### 3.10 系统用户表 `sys_user`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(100) | NOT NULL | BCrypt 哈希 |
| real_name | VARCHAR(50) | NULL | 姓名 |
| email | VARCHAR(100) | NULL | 邮箱 |
| phone | VARCHAR(20) | NULL | 手机 |
| dept | VARCHAR(100) | NULL | 部门（办事处） |
| region_scope | JSON | NULL | 负责区域 |
| status | TINYINT(1) | DEFAULT 1 | 1启用 0停用 |
| last_login_at | DATETIME | NULL | 最近登录 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

### 3.11 角色权限表

`sys_role`：id、role_name、role_code、remark、created_at、updated_at
`sys_permission`：id、perm_code（如 opp:view）、perm_name、module、created_at
`sys_user_role`：id、user_id、role_id（uk_user_role）
`sys_role_permission`：id、role_id、permission_id

### 3.12 系统配置表 `sys_config`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| config_key | VARCHAR(100) | UNIQUE, NOT NULL | 配置键 |
| config_value | TEXT | NULL | 配置值（JSON） |
| remark | VARCHAR(200) | NULL | 说明 |
| updated_by | BIGINT UNSIGNED | NULL | 更新人 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

预置配置示例：
- `scoring.weights`：`{"demand":40,"budget":20,"region":15,"urgency":15,"competition":10}`
- `push.channels`：`{"sms":false,"email":true,"webhook":true}`
- `push.daily_cron`：`"30 8 * * *"`
- `dedup.content_threshold`：`0.85`

### 3.13 审计日志表 `audit_log`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| user_id | BIGINT UNSIGNED | NULL | 操作人 |
| action | VARCHAR(50) | NOT NULL | 操作类型 |
| module | VARCHAR(50) | NULL | 模块 |
| target_id | VARCHAR(50) | NULL | 目标ID |
| detail | JSON | NULL | 变更详情 |
| ip | VARCHAR(50) | NULL | 来源IP |
| created_at | DATETIME | NOT NULL | 时间 |

索引：`idx_user(user_id)`、`idx_created(created_at)`

### 3.14 采集任务执行记录表 `collector_task_log`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| source_id | BIGINT UNSIGNED | FK | 数据源 |
| trigger_type | VARCHAR(20) | NULL | schedule/manual |
| started_at | DATETIME | NULL | 开始时间 |
| finished_at | DATETIME | NULL | 结束时间 |
| status | VARCHAR(20) | NULL | running/success/failed |
| new_count | INT | DEFAULT 0 | 新增公告数 |
| dup_count | INT | DEFAULT 0 | 去重数 |
| fail_count | INT | DEFAULT 0 | 失败数 |
| error_msg | TEXT | NULL | 错误信息 |
| created_at | DATETIME | NOT NULL | 创建时间 |

### 3.15 存量项目台账表 `legacy_project`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| project_name | VARCHAR(200) | NOT NULL | 项目名称 |
| community | VARCHAR(200) | NULL | 小区 |
| province | VARCHAR(50) | NULL | 省 |
| city | VARCHAR(50) | NULL | 市 |
| unit | VARCHAR(200) | NULL | 业主/管理单位 |
| systems | JSON | NULL | 子系统列表（门禁/对讲/监控等） |
| device_brand | VARCHAR(100) | NULL | 设备品牌 |
| install_year | INT | NULL | 安装年份 |
| contract_end_year | INT | NULL | 质保/合同到期年份 |
| est_budget | DECIMAL(12,2) | NULL | 预估预算 |
| contact | VARCHAR(100) | NULL | 联系人 |
| note | TEXT | NULL | 备注 |
| status | TINYINT(1) | DEFAULT 0 | 0在用 1已结束 2待改造 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_lp_city(province,city)`、`idx_lp_install(install_year)`

### 3.16 更新商机表 `update_opportunity`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| legacy_project_id | BIGINT UNSIGNED | FK | 来源存量项目 |
| action | VARCHAR(50) | NULL | 推荐动作（如 IP 两线换新） |
| reason | VARCHAR(200) | NULL | 生成原因（如超期/到期） |
| priority | TINYINT | DEFAULT 0 | 优先级 0低 1中 2高 |
| stage | VARCHAR(50) | NULL | 当前阶段 |
| status | TINYINT(1) | DEFAULT 0 | 0待跟进 1跟进中 2已转化 3已放弃 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_uo_project(legacy_project_id)`、`idx_uo_status(status)`

### 3.17 战略客户集采台账表 `strategic_customer`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| customer_name | VARCHAR(200) | NOT NULL | 客户名称 |
| customer_type | VARCHAR(50) | NULL | 类型（集采/战略） |
| framework_no | VARCHAR(100) | NULL | 框架协议编号 |
| contract_start_year | INT | NULL | 合同起始年份 |
| contract_end_year | INT | NULL | 合同到期年份 |
| annual_amount | DECIMAL(12,2) | NULL | 年度金额 |
| contact | VARCHAR(100) | NULL | 联系人 |
| status | TINYINT(1) | DEFAULT 0 | 0正常 1临期 2已流失 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_sc_name(customer_name)`、`idx_sc_end(contract_end_year)`

### 3.18 销售线索表 `sales_lead`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| title | VARCHAR(300) | NOT NULL | 线索标题 |
| customer_name | VARCHAR(200) | NULL | 客户名称 |
| province | VARCHAR(50) | NULL | 省 |
| city | VARCHAR(50) | NULL | 市 |
| budget | DECIMAL(12,2) | NULL | 预算金额 |
| stage | VARCHAR(50) | NULL | 阶段（初步接触/需求确认/方案报价/投标/合同谈判/已成交/已流失） |
| channel | VARCHAR(50) | NULL | 渠道（全网招标/采购意向/改造计划/立项审批/土地出让/竞品中标/销售报备等） |
| reporter_name | VARCHAR(100) | NULL | 报备人 |
| detail | TEXT | NULL | 详情（含来源 URL） |
| score | INT | DEFAULT 0 | 四维评分 0-100 |
| status | VARCHAR(20) | DEFAULT new | new/contacting/converted/lost |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_sl_status(status)`、`idx_sl_score(score)`、`idx_sl_city(province,city)`

### 3.19 竞品后续追踪表 `competitor_track`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| competitor | VARCHAR(100) | NOT NULL | 竞品名称 |
| project_name | VARCHAR(300) | NULL | 竞品项目 |
| community | VARCHAR(200) | NULL | 小区/区域 |
| province | VARCHAR(50) | NULL | 省 |
| city | VARCHAR(50) | NULL | 市 |
| won_at | DATE | NULL | 中标时间 |
| amount | DECIMAL(12,2) | NULL | 中标金额 |
| track_type | VARCHAR(50) | NULL | 追踪类型（后续标段/维保/续签） |
| source_url | VARCHAR(500) | NULL | 来源链接 |
| related_opportunity_id | BIGINT UNSIGNED | NULL | 关联商机 |
| status | VARCHAR(20) | DEFAULT tracking | tracking/won/lost |
| note | TEXT | NULL | 备注 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_ct_competitor(competitor)`、`idx_ct_city(city)`

### 3.20 诉求热点表 `appeal_hotspot`（v1.1 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT UNSIGNED | PK, AI | 主键 |
| community | VARCHAR(200) | NOT NULL | 小区 |
| province | VARCHAR(50) | NULL | 省 |
| city | VARCHAR(50) | NULL | 市 |
| appeal_count | INT | DEFAULT 0 | 投诉/诉求数量 |
| hot_score | INT | DEFAULT 0 | 热度分 0-100 |
| topics | JSON | NULL | 痛点标签 |
| sample_titles | JSON | NULL | 样本标题 |
| source_url | VARCHAR(500) | NULL | 来源链接 |
| period | VARCHAR(50) | NULL | 统计周期 |
| status | TINYINT(1) | DEFAULT 0 | 0未跟进 1已转化 |
| note | TEXT | NULL | 备注 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |
| deleted | TINYINT(1) | DEFAULT 0 | 软删除 |

索引：`idx_ah_city(city)`、`idx_ah_score(hot_score)`

---

## 4. 索引与性能策略

- 所有外键字段建索引；唯一约束防重复。
- 公告表按月/按季度考虑分区（数据量大时）。
- 驾驶舱聚合查询使用预聚合表 `agg_daily_stat`（日期+维度汇总），避免实时扫大表。
- Redis 缓存键设计：
  - `dash:overview`（5min）
  - `dedup:url:{hash}`、`dedup:content:{hash}`（去重）
  - `token:{userId}`（JWT 会话）

---

## 5. 初始化数据脚本清单

| 脚本 | 说明 |
|------|------|
| `01_schema.sql` | 建库建表 |
| `02_init_data.sql` | 角色/权限/管理员/系统配置/竞品关键词 |
| `03_product_knowledge.sql` | 产品知识库种子数据 |
| `04_regions_offices.sql` | 办事处/经销网点覆盖表 |
| `05_sources_intel_expand.sql` | 智能商机挖掘数据源种子（采购意向/改造名单/立项审批/土地出让 12 条） |
| `06_intel_schema.sql` | 智能商机挖掘 6 张业务表（存量台账/更新商机/集采台账/销售线索/竞品追踪/诉求热点） |
| `07_sources_intel_expand.sql` | 同 05（补充/修正版） |
