# -*- coding: utf-8 -*-
"""临时脚本：第五轮清理——源名标题/专栏/动态页公告（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 源名 = 标题 的公告（采集时 title 提取失败回退到 anchor 源名）
cur.execute("""SELECT a.id FROM announcement a JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status IN (0,3) AND a.title=d.source_name""")
ids = [r[0] for r in cur.fetchall()]
if ids:
    cur.executemany("UPDATE announcement SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
print('标题==源名公告软删:', len(ids))
conn.commit()

# 栏目/专栏/动态类标题
KEY = ['交易平台（', '交易专栏', '工作动态', '网上商城', '画像信息', '网上登记',
       '政府采购网', '采购公告', '合同签订公示', '出让公告', '资源交易-', '药械采购',
       '矿业权', '林权', '海洋资源', '土地及矿权', '产权交易', '国企采购', '政府采购 ']
cur.execute("SELECT id,title FROM announcement WHERE deleted=0 AND "
            "(parse_status=0 OR parse_status=3)")
rows = cur.fetchall()
ids = []
for aid, t in rows:
    t = (t or '').strip()
    if any(k in t for k in KEY):
        ids.append(aid)
if ids:
    cur.executemany("UPDATE announcement SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
print('专栏/栏目类公告软删:', len(ids))
conn.commit()

cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0")
print('剩余未解析:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3")
print('剩余待人工:', cur.fetchone()[0])
cur.execute("""SELECT a.id, a.title, d.source_name FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status IN (0,3) ORDER BY a.id""")
print('剩余待处理公告:')
for r in cur.fetchall():
    print(' ', r[0], '|', str(r[1])[:75], '|', r[2])
conn.close()
