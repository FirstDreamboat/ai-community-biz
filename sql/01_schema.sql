-- =============================================================
-- AI存量项目商机挖掘系统 - 建库建表脚本
-- 依据：《03-数据库设计说明书-DBD.md》
-- 版本：v1.0
-- =============================================================

CREATE DATABASE IF NOT EXISTS opportunity_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE opportunity_system;

-- ---------------------------------------------------------------
-- 1. 数据源表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_source (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source_name     VARCHAR(100)  NOT NULL COMMENT '数据源名称',
  source_type     VARCHAR(20)   NOT NULL COMMENT 'gov/property/policy/news/api',
  base_url        VARCHAR(500)  NULL COMMENT '站点地址',
  list_pages      JSON          NULL COMMENT '多入口列表页URL',
  spider_class    VARCHAR(100)  NULL COMMENT '爬虫类名',
  keywords        JSON          NULL COMMENT '采集关键词',
  regions         JSON          NULL COMMENT '区域范围',
  schedule_cron   VARCHAR(50)   NULL COMMENT '调度cron',
  proxy_enabled   TINYINT(1)    DEFAULT 0 COMMENT '是否代理',
  status          TINYINT(1)    DEFAULT 1 COMMENT '1启用 0停用',
  last_run_at     DATETIME      NULL COMMENT '最近运行时间',
  last_run_status VARCHAR(20)   NULL COMMENT 'success/failed/running',
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted         TINYINT(1)    DEFAULT 0 COMMENT '软删除',
  UNIQUE KEY uk_source_name (source_name, deleted),
  KEY idx_source_type (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据源表';

-- ---------------------------------------------------------------
-- 2. 公告表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcement (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fingerprint   VARCHAR(64)   NOT NULL COMMENT '去重指纹',
  source_id     BIGINT UNSIGNED NOT NULL COMMENT '数据源ID',
  source_url    VARCHAR(1000) NULL COMMENT '原始URL',
  title         VARCHAR(500)  NOT NULL COMMENT '标题',
  content       LONGTEXT      NULL COMMENT '正文(清洗后)',
  raw_html      LONGTEXT      NULL COMMENT '原始HTML',
  publish_time  DATETIME      NULL COMMENT '发布时间',
  crawl_time    DATETIME      NOT NULL COMMENT '采集时间',
  parse_status  TINYINT       DEFAULT 0 COMMENT '0待解析 1已解析 2失败 3待人工',
  category      VARCHAR(20)   NULL COMMENT 'tender/property/policy/news',
  extra         JSON          NULL COMMENT '扩展信息',
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted       TINYINT(1)    DEFAULT 0,
  UNIQUE KEY uk_fingerprint (fingerprint),
  KEY idx_source_id (source_id),
  KEY idx_publish_time (publish_time),
  KEY idx_parse_status (parse_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公告表';

-- ---------------------------------------------------------------
-- 3. 项目画像表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_profile (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  announcement_id  BIGINT UNSIGNED NOT NULL COMMENT '公告ID',
  purchaser        VARCHAR(200)   NULL COMMENT '招标方',
  project_type     VARCHAR(50)    NULL COMMENT '项目类型',
  budget           DECIMAL(14,2)  NULL COMMENT '预算(万元)',
  budget_est       TINYINT(1)     DEFAULT 0 COMMENT '是否估算',
  bid_deadline     DATETIME       NULL COMMENT '投标截止',
  open_time        DATETIME       NULL COMMENT '开标时间',
  qualification    JSON           NULL COMMENT '资质要求',
  tech_params      JSON           NULL COMMENT '技术参数',
  household_cnt    INT            NULL COMMENT '户数',
  building_cnt     INT            NULL COMMENT '楼栋数',
  area             DECIMAL(12,2)  NULL COMMENT '建筑面积(㎡)',
  contents         JSON           NULL COMMENT '改造内容标签',
  fund_source      VARCHAR(20)    NULL COMMENT '资金性质',
  stage            VARCHAR(20)    NULL COMMENT '进度阶段',
  relevance        VARCHAR(10)    NULL COMMENT '高/中/低',
  province         VARCHAR(50)    NULL COMMENT '省',
  city             VARCHAR(50)    NULL COMMENT '市',
  district         VARCHAR(50)    NULL COMMENT '区县',
  address          VARCHAR(300)   NULL COMMENT '地址',
  parsed_by        VARCHAR(50)    NULL COMMENT 'deepseek/template/human',
  human_verified   TINYINT(1)     DEFAULT 0 COMMENT '人工确认',
  created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted          TINYINT(1)     DEFAULT 0,
  UNIQUE KEY uk_announcement (announcement_id),
  KEY idx_province (province),
  KEY idx_budget (budget),
  KEY idx_stage (stage),
  KEY idx_relevance (relevance)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目画像表';

-- ---------------------------------------------------------------
-- 4. 商机表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunity (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  profile_id        BIGINT UNSIGNED NOT NULL COMMENT '项目画像ID',
  total_score       DECIMAL(5,1)    NOT NULL COMMENT '综合评分',
  demand_score      DECIMAL(4,1)    NULL COMMENT '需求匹配度(40)',
  budget_score      DECIMAL(4,1)    NULL COMMENT '预算规模(20)',
  region_score      DECIMAL(4,1)    NULL COMMENT '区域覆盖(15)',
  urgency_score     DECIMAL(4,1)    NULL COMMENT '时间紧迫度(15)',
  competition_score DECIMAL(4,1)    NULL COMMENT '竞争态势(10)',
  rules_version     VARCHAR(20)     NOT NULL COMMENT '评分规则版本',
  level             VARCHAR(10)     NULL COMMENT '高/中/低评分段',
  status            VARCHAR(20)     DEFAULT 'new' COMMENT 'new/following/bid/won/lost/closed',
  owner_id          BIGINT UNSIGNED NULL COMMENT '负责销售',
  assign_time       DATETIME        NULL COMMENT '分配时间',
  recommend_reason  TEXT            NULL COMMENT '推荐理由',
  follow_strategy   JSON            NULL COMMENT '跟进策略',
  score_at          DATETIME        NOT NULL COMMENT '评分时间',
  created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted           TINYINT(1)      DEFAULT 0,
  UNIQUE KEY uk_profile (profile_id),
  KEY idx_status (status),
  KEY idx_level (level),
  KEY idx_owner (owner_id),
  KEY idx_score (total_score),
  KEY idx_score_at (score_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商机表';

-- ---------------------------------------------------------------
-- 5. 跟进记录表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS follow_up_log (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  opportunity_id  BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NOT NULL,
  action          VARCHAR(50)     NOT NULL COMMENT '动作',
  from_status     VARCHAR(20)     NULL,
  to_status       VARCHAR(20)     NULL,
  note            TEXT            NULL COMMENT '跟进说明',
  next_plan       VARCHAR(500)    NULL COMMENT '下一步计划',
  follow_time     DATETIME        NOT NULL COMMENT '跟进时间',
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_opportunity (opportunity_id),
  KEY idx_user (user_id),
  KEY idx_follow_time (follow_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='跟进记录表';

-- ---------------------------------------------------------------
-- 6. 推送记录表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS push_record (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  opportunity_id   BIGINT UNSIGNED NOT NULL,
  push_channel     VARCHAR(20)     NOT NULL COMMENT 'sms/email/webhook',
  receiver         VARCHAR(200)    NOT NULL COMMENT '接收人',
  push_date        DATE            NOT NULL COMMENT '推送日期',
  content_snapshot JSON            NULL COMMENT '内容快照',
  status           VARCHAR(20)     DEFAULT 'pending' COMMENT 'pending/success/failed',
  error_msg        VARCHAR(500)    NULL COMMENT '失败原因',
  created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_opp_channel_date (opportunity_id, push_channel, push_date),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送记录表';

-- ---------------------------------------------------------------
-- 7. 竞品监测表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competitor_record (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  competitor      VARCHAR(50)     NOT NULL COMMENT '竞品名称',
  announcement_id BIGINT UNSIGNED NULL,
  profile_id      BIGINT UNSIGNED NULL,
  province        VARCHAR(50)     NULL,
  result          VARCHAR(20)     NULL COMMENT '中标/投标',
  amount          DECIMAL(14,2)   NULL COMMENT '金额(万元)',
  detected_at     DATETIME        NOT NULL COMMENT '发现时间',
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_competitor (competitor),
  KEY idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞品监测表';

-- ---------------------------------------------------------------
-- 8. 产品知识库表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_knowledge (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(200) NOT NULL COMMENT '知识标题',
  category    VARCHAR(50)  NOT NULL COMMENT '分类',
  content     TEXT         NOT NULL COMMENT '内容/方案描述',
  tags        JSON         NULL COMMENT '能力标签',
  vector_id   VARCHAR(64)  NULL COMMENT '向量库ID',
  status      TINYINT(1)   DEFAULT 1,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品知识库表';

-- ---------------------------------------------------------------
-- 9. 政策信息表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS policy_info (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title           VARCHAR(500) NOT NULL COMMENT '政策标题',
  level           VARCHAR(20)  NULL COMMENT '国家级/省级/市级',
  region          VARCHAR(100) NULL COMMENT '发布地区',
  content         TEXT         NULL,
  publish_time    DATETIME     NULL,
  announcement_ids JSON        NULL COMMENT '关联公告ID',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='政策信息表';

-- ---------------------------------------------------------------
-- 10. 办事处/经销网点覆盖表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS office (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  office_name VARCHAR(100) NOT NULL COMMENT '办事处名称',
  office_type VARCHAR(20)  DEFAULT '直属' COMMENT '直属/经销',
  province    VARCHAR(50)  NOT NULL COMMENT '省',
  city        VARCHAR(50)  NULL COMMENT '市',
  cover_type  VARCHAR(20)  DEFAULT 'cover' COMMENT 'cover/radiate/none',
  address     VARCHAR(300) NULL,
  contact     VARCHAR(50)  NULL,
  status      TINYINT(1)   DEFAULT 1,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='办事处覆盖表';

-- ---------------------------------------------------------------
-- 11. 系统用户表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sys_user (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL,
  password_hash VARCHAR(100) NOT NULL COMMENT 'BCrypt哈希',
  real_name     VARCHAR(50)  NULL,
  email         VARCHAR(100) NULL,
  phone         VARCHAR(20)  NULL,
  dept          VARCHAR(100) NULL COMMENT '部门(办事处)',
  region_scope  JSON         NULL COMMENT '负责区域',
  status        TINYINT(1)   DEFAULT 1,
  last_login_at DATETIME     NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted       TINYINT(1)   DEFAULT 0,
  UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

-- ---------------------------------------------------------------
-- 12. 角色权限相关表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sys_role (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_name  VARCHAR(50)  NOT NULL,
  role_code  VARCHAR(50)  NOT NULL,
  remark     VARCHAR(200) NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

CREATE TABLE IF NOT EXISTS sys_permission (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  perm_code  VARCHAR(100) NOT NULL COMMENT '权限码',
  perm_name  VARCHAR(100) NULL,
  module     VARCHAR(50)  NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_perm_code (perm_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

CREATE TABLE IF NOT EXISTS sys_user_role (
  id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  role_id BIGINT UNSIGNED NOT NULL,
  UNIQUE KEY uk_user_role (user_id, role_id),
  KEY idx_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

CREATE TABLE IF NOT EXISTS sys_role_permission (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  role_id       BIGINT UNSIGNED NOT NULL,
  permission_id BIGINT UNSIGNED NOT NULL,
  UNIQUE KEY uk_role_permission (role_id, permission_id),
  KEY idx_permission (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- ---------------------------------------------------------------
-- 13. 系统配置表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sys_config (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  config_key   VARCHAR(100) NOT NULL,
  config_value TEXT         NULL,
  remark       VARCHAR(200) NULL,
  updated_by   BIGINT UNSIGNED NULL,
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ---------------------------------------------------------------
-- 14. 审计日志表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NULL,
  action     VARCHAR(50) NOT NULL,
  module     VARCHAR(50) NULL,
  target_id  VARCHAR(50) NULL,
  detail     JSON        NULL,
  ip         VARCHAR(50) NULL,
  created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user (user_id),
  KEY idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审计日志表';

-- ---------------------------------------------------------------
-- 15. 采集任务执行记录表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collector_task_log (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source_id    BIGINT UNSIGNED NOT NULL,
  trigger_type VARCHAR(20)  NULL COMMENT 'schedule/manual',
  started_at   DATETIME     NULL,
  finished_at  DATETIME     NULL,
  status       VARCHAR(20)  NULL COMMENT 'running/success/failed',
  new_count    INT DEFAULT 0,
  dup_count    INT DEFAULT 0,
  fail_count   INT DEFAULT 0,
  error_msg    TEXT         NULL,
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_source (source_id),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集任务记录表';

-- ---------------------------------------------------------------
-- 16. 每日聚合统计表（驾驶舱预聚合）
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agg_daily_stat (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  stat_date     DATE NOT NULL,
  dimension     VARCHAR(30) NOT NULL COMMENT 'region/score/status/level',
  dim_key       VARCHAR(100) NOT NULL COMMENT '维度值(省/分桶/状态)',
  dim_value     VARCHAR(100) NULL,
  count_value   INT NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_stat (stat_date, dimension, dim_key),
  KEY idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日聚合统计表';
