# -*- coding: utf-8 -*-
"""临时脚本：存量垃圾清理（用完删除）
1) 软删 rel=低 的无关注机
2) 软删黄页垃圾公告（未解析的）
3) 软删标题异常公告（==源名 / 过短）
"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 1. rel=低 商机软删
cur.execute("""UPDATE opportunity o JOIN project_profile p ON o.profile_id=p.id
  SET o.deleted=1, o.updated_at=NOW()
  WHERE o.deleted=0 AND p.relevance='低'""")
print('rel=低 商机软删:', cur.rowcount)

# 2. 黄页特征公告软删（未解析的）
cur.execute("""UPDATE announcement SET deleted=1, updated_at=NOW()
  WHERE deleted=0 AND parse_status=0 AND (
   title LIKE '%价格%' OR title LIKE '%报价%' OR title LIKE '%厂家%'
   OR title LIKE '%批发%' OR title LIKE '%供应%' OR title LIKE '%规格%'
   OR title LIKE '%型号%' OR title LIKE '%经销商%' OR title LIKE '%产品大全%'
   OR title LIKE '%产品目录%' OR title LIKE '%多少钱%' OR title LIKE '%哪家好%')""")
print('黄页公告软删:', cur.rowcount)

# 3. 标题==源名的公告软删
cur.execute("""UPDATE announcement a JOIN data_source d ON a.source_id=d.id
  SET a.deleted=1, a.updated_at=NOW()
  WHERE a.deleted=0 AND a.title=d.source_name""")
print('标题==源名公告软删:', cur.rowcount)

# 4. 标题过短(<6字)且未解析的公告软删
cur.execute("""UPDATE announcement SET deleted=1, updated_at=NOW()
  WHERE deleted=0 AND parse_status=0 AND (title IS NULL OR CHAR_LENGTH(TRIM(title))<6)""")
print('标题过短未解析公告软删:', cur.rowcount)

conn.commit()

# 清理后统计
cur.execute("SELECT COUNT(*) FROM opportunity WHERE deleted=0")
print('清理后商机数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0")
print('清理后公告数:', cur.fetchone()[0])
cur.execute("SELECT p.relevance, COUNT(*) FROM opportunity o "
            "JOIN project_profile p ON o.profile_id=p.id "
            "WHERE o.deleted=0 GROUP BY p.relevance")
print('清理后商机相关度分布:', cur.fetchall())
conn.close()
