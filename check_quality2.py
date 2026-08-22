# -*- coding: utf-8 -*-
"""临时脚本：商机质量分布分析（用完删除）"""
import pymysql, json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 1. 商机相关性分布
cur.execute("""SELECT p.relevance, COUNT(*) FROM opportunity o
               JOIN project_profile p ON o.profile_id=p.id
               WHERE o.deleted=0 GROUP BY p.relevance""")
print('== 商机相关性分布 ==')
for r in cur.fetchall():
    print('  rel=', r[0], ':', r[1])

# 2. contents 为空的比例
cur.execute("""SELECT COUNT(*) FROM opportunity o
               JOIN project_profile p ON o.profile_id=p.id
               WHERE o.deleted=0 AND (p.contents IS NULL OR p.contents='[]')""")
print('contents 为空的商机数:', cur.fetchone()[0])

# 3. 分数分布
cur.execute("""SELECT o.level, COUNT(*) FROM opportunity o WHERE o.deleted=0 GROUP BY o.level""")
print('== 商机等级分布 ==')
for r in cur.fetchall():
    print('  level=', r[0], ':', r[1])

# 4. verify detail 的 suggested_relevance
cur.execute("""SELECT o.verify_status, COUNT(*) FROM opportunity o WHERE o.deleted=0 GROUP BY o.verify_status""")
print('== 商机核验状态 ==')
for r in cur.fetchall():
    print('  verify=', r[0], ':', r[1])

# 5. 低质商机明细
cur.execute("""SELECT o.id, p.relevance, p.project_type, p.contents, o.total_score,
                      a.title, o.verify_note
               FROM opportunity o
               JOIN project_profile p ON o.profile_id=p.id
               JOIN announcement a ON p.announcement_id=a.id
               WHERE o.deleted=0 AND (p.relevance='低' OR p.contents IS NULL OR p.contents='[]')
               ORDER BY o.id DESC LIMIT 30""")
print('== 低质商机明细 ==')
for r in cur.fetchall():
    print('O', r[0], '|rel=' + str(r[1]), '|type=' + str(r[2])[:20],
          '|cont=' + str(r[3])[:40], '|score=' + str(r[4]), '|', str(r[5])[:45])

# 6. 每条公告来源分布（找出垃圾源）
cur.execute("""SELECT d.source_name, COUNT(*) FROM announcement a
               JOIN data_source d ON a.source_id=d.id
               WHERE a.deleted=0 GROUP BY d.source_name ORDER BY COUNT(*) DESC LIMIT 15""")
print('== 公告来源 TOP ==')
for r in cur.fetchall():
    print('  ', r[0], ':', r[1])

conn.close()
