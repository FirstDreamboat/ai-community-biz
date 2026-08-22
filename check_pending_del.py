# -*- coding: utf-8 -*-
"""临时脚本：检查待删商机的原始值（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor(pymysql.cursors.DictCursor)
cur.execute("""SELECT o.id, a.title, p.contents, p.relevance FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  WHERE o.deleted=0 AND (p.contents IS NULL OR p.contents='[]' OR a.title LIKE '%测试%')
  ORDER BY o.id""")
for r in cur.fetchall():
    print(r['id'], '|title=', repr(r['title'][:40]), '|contents=', repr(r['contents']),
          '|rel=', r['relevance'])
conn.close()
