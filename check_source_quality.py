# -*- coding: utf-8 -*-
"""临时脚本：数据源产出质量分析（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

print('== 各数据源公告数/解析/待人工 ==')
cur.execute("""
  SELECT d.id, d.source_name, d.source_type,
         COUNT(a.id) ann_cnt,
         SUM(CASE WHEN a.parse_status=1 THEN 1 ELSE 0 END) parsed,
         SUM(CASE WHEN a.parse_status=3 THEN 1 ELSE 0 END) manual
  FROM data_source d LEFT JOIN announcement a ON a.source_id=d.id AND a.deleted=0
  WHERE d.deleted=0
  GROUP BY d.id, d.source_name, d.source_type
  HAVING ann_cnt > 0
  ORDER BY ann_cnt DESC""")
for r in cur.fetchall():
    print(f"  [{r[2]}] id={r[0]} {r[1]}: 公告{r[3]} 解析{r[4]} 待人工{r[5]}")

conn.close()
