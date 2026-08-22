# -*- coding: utf-8 -*-
"""临时脚本：查看高/中相关商机明细（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute("""SELECT o.id, p.relevance, p.contents, o.total_score, o.status, a.title
               FROM opportunity o
               JOIN project_profile p ON o.profile_id=p.id
               JOIN announcement a ON p.announcement_id=a.id
               WHERE o.deleted=0 AND p.relevance IN ('高','中')
               ORDER BY p.relevance DESC, o.total_score DESC""")
for r in cur.fetchall():
    print('O', r[0], '|rel=' + str(r[1]), '|cont=' + str(r[2]), '|score=' + str(r[3]),
          '|st=' + str(r[4]), '|', str(r[5])[:70])
conn.close()
