# -*- coding: utf-8 -*-
"""临时脚本：第六轮清理——软删剩余全部低质待处理公告（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute("""UPDATE announcement SET deleted=1, updated_at=NOW()
  WHERE deleted=0 AND parse_status IN (0,3)""")
print('剩余低质待处理公告软删:', cur.rowcount)
conn.commit()

# 汇总统计
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0")
print('公告总数(未删):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=1")
print('已解析公告:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM opportunity WHERE deleted=0")
print('商机数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM data_source WHERE deleted=0 AND status=1")
print('启用数据源:', cur.fetchone()[0])
conn.close()
