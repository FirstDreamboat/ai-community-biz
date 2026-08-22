# -*- coding: utf-8 -*-
"""临时脚本：查看政府采购/公共资源类源（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
cur.execute("SELECT id,source_name,status,last_run_status FROM data_source "
            "WHERE source_name LIKE '%政府采购%' OR source_name LIKE '%公共资源%' ORDER BY id")
for r in cur.fetchall():
    print(r)
conn.close()
