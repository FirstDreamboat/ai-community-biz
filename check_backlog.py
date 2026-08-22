# -*- coding: utf-8 -*-
"""临时脚本：未解析/待人工公告来源质量分析（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

print('== 未解析(parse_status=0)公告按来源 ==')
cur.execute("""SELECT d.source_name, COUNT(*) c FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status=0 GROUP BY d.source_name ORDER BY c DESC LIMIT 20""")
for r in cur.fetchall():
    print('  ', r[0], ':', r[1])

print()
print('== 待人工(parse_status=3)公告按来源 ==')
cur.execute("""SELECT d.source_name, COUNT(*) c FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status=3 GROUP BY d.source_name ORDER BY c DESC LIMIT 20""")
for r in cur.fetchall():
    print('  ', r[0], ':', r[1])

print()
print('== 未解析公告标题示例（前20条）==')
cur.execute("""SELECT a.title, d.source_name FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status=0 ORDER BY a.id DESC LIMIT 20""")
for r in cur.fetchall():
    print('  ', str(r[0])[:55], '|', r[1])

print()
print('== 待人工公告标题示例（前15条）==')
cur.execute("""SELECT a.title, d.source_name FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status=3 ORDER BY a.id DESC LIMIT 15""")
for r in cur.fetchall():
    print('  ', str(r[0])[:55], '|', r[1])

conn.close()
