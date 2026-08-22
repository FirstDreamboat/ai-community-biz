# -*- coding: utf-8 -*-
"""临时脚本：第二轮存量清理（导航/栏目页垃圾公告）+ 停用纯垃圾源（用完删除）"""
import pymysql, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

NAV = ['登录', '注册', '首页', '设为首页', '收藏本站', '平台入口', '系统入口',
       '监督平台', '交易平台首页', '帮助中心', '下载中心', '联系我们', '关于我们',
       '友情链接', '网站地图', '返回首页', '网站首页', '用户中心', '个人中心',
       '在线客服', '证书', '办事指南', '服务指南', '政策法规', '政策文件',
       '信息公开', '机构职能', '领导信箱', '互动交流', '无障碍', '旧版']

# 1. 标题含导航词 或 标题含栏目聚合特征（_分隔/以网结尾）的未解析公告软删
col_re = re.compile(r'[_\uFF5C|]|-[^\s]{1,12}网$')
cur.execute("SELECT id,title FROM announcement WHERE deleted=0 AND parse_status=0")
rows = cur.fetchall()
ids = []
for aid, t in rows:
    t = t or ''
    if any(k in t for k in NAV) or col_re.search(t) or len(t.strip()) < 6:
        ids.append(aid)
if ids:
    cur.executemany("UPDATE announcement SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
print('导航/栏目页垃圾公告软删:', len(ids))
conn.commit()

# 2. 清理后统计
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0")
print('剩余未解析:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3")
print('待人工:', cur.fetchone()[0])

# 3. 停用纯垃圾源（公告30+但解析0，采的全是导航页）
cur.execute("""
  SELECT d.id, d.source_name, COUNT(a.id) ann_cnt
  FROM data_source d JOIN announcement a ON a.source_id=d.id AND a.deleted=0
  WHERE d.deleted=0 AND d.source_type IN ('gov','news')
  GROUP BY d.id, d.source_name HAVING ann_cnt >= 30
  AND SUM(CASE WHEN a.parse_status IN (1,3) THEN 1 ELSE 0 END) = 0""")
bad = cur.fetchall()
for r in bad:
    print('纯垃圾源:', r[0], r[1], '公告', r[2])
    cur.execute("UPDATE data_source SET status=0, updated_at=NOW() WHERE id=%s", (r[0],))
conn.commit()
print('停用纯垃圾源:', len(bad))
conn.close()
