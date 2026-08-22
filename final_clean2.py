# -*- coding: utf-8 -*-
"""临时脚本：按实际内容清理低质商机（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor(pymysql.cursors.DictCursor)

# 主营关键词（标题含这些词的保留）
BIZ = ['对讲', '智能家居', '医护', '病房', '门禁', '安防', '监控', '智能化', '弱电',
       '智慧', '停车', '照明', '老旧小区', '技防', '医院', '医疗', '康养', '医养',
       '物业管理', '物业服务', '校园', '改造', '设备', '系统集成', '综合布线']

cur.execute("""SELECT o.id, a.title, p.contents FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  WHERE o.deleted=0 ORDER BY o.id""")
rows = cur.fetchall()
ids = []
for r in rows:
    title = r['title'] or ''
    contents = r['contents']
    # 内容为空/无效
    empty = contents is None
    if isinstance(contents, str):
        s = contents.strip()
        empty = empty or s == '' or s == '[]' or s == 'null' or s == 'NULL' or s == 'None'
    # 测试数据
    is_test = '测试' in title
    # 无主营内容标签 且 标题也无主营词 -> 低质
    has_biz = any(k in title for k in BIZ)
    if empty and not has_biz:
        ids.append(r['id'])
    elif is_test:
        ids.append(r['id'])
if ids:
    cur.executemany("UPDATE opportunity SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
    print('删除低质商机:', len(ids), ids)
conn.commit()

cur.execute("SELECT COUNT(*) c FROM opportunity WHERE deleted=0")
print('最终商机数:', cur.fetchone()['c'])
cur.execute("""SELECT o.id, p.relevance, p.contents, o.total_score, o.level, a.title
  FROM opportunity o
  JOIN project_profile p ON o.profile_id=p.id
  JOIN announcement a ON p.announcement_id=a.id
  WHERE o.deleted=0 ORDER BY p.relevance DESC, o.total_score DESC""")
for r in cur.fetchall():
    print('O', r['id'], '|rel=' + str(r['relevance']), '|cont=' + str(r['contents']),
          '|score=' + str(r['total_score']), '|lvl=' + str(r['level']),
          '|', str(r['title'])[:70])
conn.close()
