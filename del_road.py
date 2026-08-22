# -*- coding: utf-8 -*-
"""临时脚本：删除剩余纯市政/土建商机（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
# O22 铸造厂道路规范化改造（纯道路工程）、O42 地铁市政管线及道路恢复（纯市政工程）
cur.execute("UPDATE opportunity SET deleted=1, updated_at=NOW() WHERE id IN (22, 42)")
print('删除纯市政商机:', cur.rowcount)
conn.commit()
conn.close()
