# -*- coding: utf-8 -*-
"""临时脚本：最终清理——删除 cont=[] 且标题无主营词的商机 + 测试数据（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 主营关键词（标题含这些词的保留）
BIZ = ['对讲', '智能家居', '医护', '病房', '门禁', '安防', '监控', '智能化', '弱电',
       '智慧', '停车', '照明', '老旧小区', '技防', '医院', '医疗', '康养', '医养',
       '物业管理', '物业服务', '校园', '改造', '设备', '系统集成', '综合布线']

cur.execute("""SELECT o.id, a.title, p.contents FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  WHERE o.deleted=0 AND (p.contents IS NULL OR p.contents='[]' OR a.title LIKE '%测试%')""")
rows = cur.fetchall()
ids = []
for oid, title, contents in rows:
    title = title or ''
    if '%测试%' in str(title) or not any(k in title for k in BIZ):
        ids.append(oid)
if ids:
    cur.executemany("UPDATE opportunity SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
    print('删除低质商机:', len(ids))
conn.commit()

cur.execute("SELECT COUNT(*) FROM opportunity WHERE deleted=0")
print('最终商机数:', cur.fetchone()[0])
cur.execute("""SELECT o.id, p.relevance, p.contents, o.total_score, o.level, a.title
  FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  WHERE o.deleted=0 ORDER BY p.relevance DESC, o.total_score DESC""")
for r in cur.fetchall():
    print('O', r[0], '|rel=' + str(r[1]), '|cont=' + str(r[2]), '|score=' + str(r[3]),
          '|lvl=' + str(r[4]), '|', str(r[5])[:70])
conn.close()
