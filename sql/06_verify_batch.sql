-- ============================================================
-- 06_verify_batch.sql  AI二次核验 + 批量解析 支持
-- 说明：
--   1) announcement 增加核验字段（verify_status / verify_result / parse_error）
--   2) opportunity 增加核验状态快照（verify_status / verify_note）
-- 用途：防止生成假商机——公告解析后先经 AI 二次核验，
--       核验通过才生成商机；核验不通过/待人工的不自动生成。
-- ============================================================

ALTER TABLE announcement
  ADD COLUMN verify_status TINYINT NOT NULL DEFAULT 0
    COMMENT 'AI二次核验状态:0未核验 1通过 2不通过 3待人工' AFTER parse_status,
  ADD COLUMN verify_result JSON NULL
    COMMENT 'AI核验详情(结论/理由/风险点/无依据字段)' AFTER verify_status,
  ADD COLUMN parse_error VARCHAR(500) NULL
    COMMENT '最近一次解析/核验错误信息' AFTER verify_result;

ALTER TABLE opportunity
  ADD COLUMN verify_status TINYINT NOT NULL DEFAULT 0
    COMMENT '商机核验状态:0未核验 1通过 2不通过 3待人工' AFTER status,
  ADD COLUMN verify_note VARCHAR(500) NULL
    COMMENT '商机核验备注(结论简述)' AFTER verify_status;
