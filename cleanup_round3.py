# -*- coding: utf-8 -*-
"""临时脚本：第三轮清理——已停用源公告 + 导航标题公告，然后统计有效可重跑公告（用完删除）"""
import pymysql, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 1. 已停用源(status=0)的公告软删
cur.execute("""UPDATE announcement a JOIN data_source d ON a.source_id=d.id
  SET a.deleted=1, a.updated_at=NOW()
  WHERE a.deleted=0 AND d.status=0""")
print('已停用源公告软删:', cur.rowcount)
conn.commit()

# 2. 标题为导航/源名/栏目特征的公告软删（无论解析状态）
NAV = ['登录', '注册', '平台入口', '系统入口', '监督平台', '帮助中心', '下载中心',
       '联系我们', '关于我们', '友情链接', '网站地图', '办事指南', '服务指南',
       '交易平台首页', '返回首页', '网站首页', '用户中心', '个人中心', '在线客服']
col_re = re.compile(r'[_\uFF5C|]')
cur.execute("SELECT id,title FROM announcement WHERE deleted=0 AND "
            "(parse_status=0 OR parse_status=3)")
rows = cur.fetchall()
ids = []
for aid, t in rows:
    t = (t or '').strip()
    # 源名样标题：XX交易网/XX平台 且无招标语义
    is_nav = any(k in t for k in NAV)
    is_portal = (t.endswith('交易网') or t.endswith('交易平台') or t.endswith('交易系统')
                 or t.endswith('服务网') or t.endswith('服务平台') or t == '登录'
                 or '登录到' in t) and not any(k in t for k in ['招标', '采购', '公告', '磋商', '询价'])
    if is_nav or is_portal or col_re.search(t) or len(t) < 6:
        ids.append(aid)
if ids:
    cur.executemany("UPDATE announcement SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
print('导航/源名标题公告软删:', len(ids))
conn.commit()

# 3. 统计剩余有效待处理公告
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0")
print('剩余未解析:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3")
print('剩余待人工:', cur.fetchone()[0])
cur.execute("""SELECT d.source_name, a.parse_status, COUNT(*) c FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status IN (0,3)
  GROUP BY d.source_name, a.parse_status ORDER BY c DESC LIMIT 30""")
print('剩余有效待处理公告按来源:')
for r in cur.fetchall():
    print('  ', r[0], '| parse=' + str(r[1]), ':', r[2])
conn.close()
