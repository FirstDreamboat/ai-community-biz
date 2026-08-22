# -*- coding: utf-8 -*-
"""临时脚本：确认垃圾公告规模 + 商机状态（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 1. 黄页特征公告统计（标题含价格/型号/厂家等）
cur.execute("""SELECT COUNT(*) FROM announcement WHERE deleted=0 AND
  (title LIKE '%价格%' OR title LIKE '%型号%' OR title LIKE '%厂家%'
   OR title LIKE '%报价%' OR title LIKE '%供应%' OR title LIKE '%批发%'
   OR title LIKE '%规格%' OR title LIKE '%参数%' OR title LIKE '%经销商%'
   OR title LIKE '%产品大全%' OR title LIKE '%产品目录%' OR title LIKE '%公司简介%')""")
print('黄页特征公告数:', cur.fetchone()[0])

# 2. 按来源统计黄页公告
cur.execute("""SELECT d.source_name, COUNT(*) FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND (a.title LIKE '%价格%' OR a.title LIKE '%型号%'
   OR a.title LIKE '%厂家%' OR a.title LIKE '%报价%' OR a.title LIKE '%供应%'
   OR a.title LIKE '%批发%' OR a.title LIKE '%规格%' OR a.title LIKE '%参数%')
  GROUP BY d.source_name ORDER BY COUNT(*) DESC LIMIT 10""")
print('黄页公告按来源:')
for r in cur.fetchall():
    print('  ', r[0], ':', r[1])

# 3. 商机 status 分布
cur.execute("""SELECT status, COUNT(*) FROM opportunity WHERE deleted=0 GROUP BY status""")
print('商机 status 分布:', cur.fetchall())

# 4. rel=低 商机对应公告标题示例
cur.execute("""SELECT a.title, d.source_name FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  JOIN data_source d ON a.source_id=d.id
  WHERE o.deleted=0 AND p.relevance='低' LIMIT 12""")
print('rel=低 商机示例:')
for r in cur.fetchall():
    print('  ', str(r[0])[:60], '|', r[1])

conn.close()
