-- =============================================================
-- 初始化数据：角色/权限/管理员/系统配置/竞品关键词
-- 版本：v1.0
-- =============================================================
USE opportunity_system;

-- ---------------------------------------------------------------
-- 1. 角色
-- ---------------------------------------------------------------
INSERT INTO sys_role (role_name, role_code, remark) VALUES
('系统管理员', 'admin', '全部权限'),
('业务顾问',   'business_consultant', '评分规则、知识库维护'),
('销售经理',   'sales_manager', '商机分配、团队跟进管理'),
('销售人员',   'sales', '商机查看、跟进'),
('只读用户',   'viewer', '驾驶舱、报表只读');

-- ---------------------------------------------------------------
-- 2. 权限
-- ---------------------------------------------------------------
INSERT INTO sys_permission (perm_code, perm_name, module) VALUES
('opp:view',    '商机查看',   'opportunity'),
('opp:follow',  '商机跟进',   'opportunity'),
('opp:assign',  '商机分配',   'opportunity'),
('data:view',   '数据源查看', 'data'),
('data:manage', '数据源管理', 'data'),
('sys:user:view',    '用户查看', 'system'),
('sys:user:manage',  '用户管理', 'system'),
('sys:config:view',  '配置查看', 'system'),
('sys:config:manage','配置管理', 'system'),
('sys:audit:view',   '审计查看', 'system'),
('knowledge:view',   '知识库查看', 'knowledge'),
('knowledge:manage', '知识库管理', 'knowledge');

-- ---------------------------------------------------------------
-- 3. 角色-权限绑定
-- ---------------------------------------------------------------
-- admin：全部
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p WHERE r.role_code = 'admin';
-- business_consultant：商机查看/跟进 + 知识库管理
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p
WHERE r.role_code = 'business_consultant'
  AND p.perm_code IN ('opp:view','opp:follow','knowledge:view','knowledge:manage');
-- sales_manager：商机查看/跟进/分配
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p
WHERE r.role_code = 'sales_manager'
  AND p.perm_code IN ('opp:view','opp:follow','opp:assign');
-- sales：商机查看/跟进
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p
WHERE r.role_code = 'sales' AND p.perm_code IN ('opp:view','opp:follow');
-- viewer：商机查看
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT r.id, p.id FROM sys_role r, sys_permission p
WHERE r.role_code = 'viewer' AND p.perm_code IN ('opp:view');

-- ---------------------------------------------------------------
-- 4. 管理员账号（初始密码 admin123，首登后修改）
-- ---------------------------------------------------------------
-- 密码哈希由应用侧生成后替换，此处先插入占位（BCrypt of "admin123"）
INSERT INTO sys_user (username, password_hash, real_name, dept, status)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyDAVYc4bGUQeK', '系统管理员', '信息中心', 1);

INSERT INTO sys_user_role (user_id, role_id)
SELECT u.id, r.id FROM sys_user u, sys_role r WHERE u.username = 'admin' AND r.role_code = 'admin';

-- ---------------------------------------------------------------
-- 5. 系统配置
-- ---------------------------------------------------------------
INSERT INTO sys_config (config_key, config_value, remark) VALUES
('scoring.weights', '{"demand":40,"budget":20,"region":15,"urgency":15,"competition":10}', '商机评分权重'),
('scoring.budget_segments', '{"1000":20,"500":16,"100":12,"0":6}', '预算分段阈值(万元):得分'),
('scoring.urgency_days', '{"7":15,"30":12,"90":8,"999":5}', '时间紧迫度(天):得分'),
('scoring.competition', '{"none":10,"one":7,"many":4,"won":2}', '竞争态势得分'),
('scoring.level', '{"high":70,"medium":40,"low":0}', '评分段阈值'),
('push.channels', '{"sms":false,"email":true,"webhook":true}', '推送渠道开关'),
('push.daily_cron', '30 8 * * *', '每日推荐列表推送时间'),
('push.weekly_cron', '0 9 * * 1', '每周推荐列表推送时间'),
('dedup.content_threshold', '0.85', '内容相似度阈值'),
('competitor.keywords', '["安居宝","立林","视得安","慧锐通","三星门禁"]', '竞品关键词库'),
('system.relevance_threshold', '{"high":0.8,"medium":0.5,"low":0}', '相关度判定阈值');

-- ---------------------------------------------------------------
-- 6. 数据源预置示例
-- ---------------------------------------------------------------
INSERT INTO data_source (source_name, source_type, base_url, spider_class, keywords, regions, schedule_cron, proxy_enabled, status) VALUES
('中国政府采购网', 'gov', 'https://www.ccgp.gov.cn', 'GovTenderSpider', '["老旧小区改造","城市更新","楼宇对讲","门禁","安防"]', '["全国"]', '0 6 * * *', 1, 1),
('福建省公共资源交易中心', 'gov', 'https://ggzyfw.fujian.gov.cn', 'RegionalTenderSpider', '["老旧小区改造","智慧社区"]', '["福建"]', '0 7 * * *', 1, 1),
('厦门市公共资源交易网', 'gov', 'https://ggzy.xm.gov.cn', 'RegionalTenderSpider', '["老旧小区改造","城市更新"]', '["厦门"]', '0 7 * * *', 1, 1),
('住建部官网', 'gov', 'https://www.mohurd.gov.cn', 'GovTenderSpider', '["老旧小区","城市更新","改造"]', '["全国"]', '0 8 * * 1', 0, 1);
