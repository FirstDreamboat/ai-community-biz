# -*- coding: utf-8 -*-
"""临时脚本：待人工公告标题预览（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute("""SELECT a.id, a.title, d.source_name FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status=3 ORDER BY a.id DESC LIMIT 60""")
for r in cur.fetchall():
    print(r[0], '|', str(r[1])[:75], '|', r[2])
conn.close()
