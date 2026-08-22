# -*- coding: utf-8 -*-
"""临时脚本：查看商机列表数据质量（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM opportunity WHERE deleted=0")
print('opportunity total:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM project_profile WHERE deleted=0")
print('project_profile total:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0")
print('announcement total:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3")
print('announcement 待人工(parse_status=3):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0")
print('announcement 未解析(parse_status=0):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=1")
print('announcement 已解析(parse_status=1):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=2")
print('announcement 解析失败(parse_status=2):', cur.fetchone()[0])

print()
cur.execute("SELECT a.id,a.title,d.source_name,a.parse_status,a.verify_status FROM announcement a "
            "LEFT JOIN data_source d ON a.source_id=d.id "
            "WHERE a.deleted=0 ORDER BY a.id DESC LIMIT 30")
for r in cur.fetchall():
    print('A', r[0], '|', str(r[1])[:55], '|', str(r[2])[:20], '|parse=' + str(r[3]), '|verify=' + str(r[4]))

print()
cur.execute("SELECT p.id, p.announcement_id, p.purchaser, p.project_type, p.budget, "
            "p.contents, p.relevance, p.province, p.city, p.stage, p.human_verified, "
            "o.level, o.total_score, o.status "
            "FROM project_profile p LEFT JOIN opportunity o ON o.profile_id=p.id "
            "WHERE p.deleted=0 ORDER BY p.id DESC LIMIT 25")
for r in cur.fetchall():
    print('P', r[0], '|ann=' + str(r[1]), '|', str(r[2])[:25], '|', str(r[3]), '|budget=' + str(r[4]),
          '|contents=' + str(r[5]), '|rel=' + str(r[6]), '|', str(r[7]), str(r[8]),
          '|stage=' + str(r[9]), '|hv=' + str(r[10]), '|lvl=' + str(r[11]),
          '|score=' + str(r[12]), '|st=' + str(r[13]))

conn.close()
