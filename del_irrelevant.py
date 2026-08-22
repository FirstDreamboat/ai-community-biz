# -*- coding: utf-8 -*-
"""临时脚本：删除剩余明显无关商机（O10 变电站设备、O27 供水管道）（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()
# O10 变电站改造（电力设备，与弱电智能化无关）、O27 供水管道工程（纯市政管网）
cur.execute("UPDATE opportunity SET deleted=1, updated_at=NOW() WHERE id IN (10, 27)")
print('删除无关商机:', cur.rowcount)
conn.commit()

cur.execute("SELECT COUNT(*) FROM opportunity WHERE deleted=0")
print('最终商机数:', cur.fetchone()[0])
conn.close()
