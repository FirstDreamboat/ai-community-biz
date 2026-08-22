# -*- coding: utf-8 -*-
"""临时脚本：统计标题异常公告（用完删除）"""
import pymysql, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

# 标题为空/过短
cur.execute("""SELECT COUNT(*) FROM announcement WHERE deleted=0 AND (title IS NULL OR CHAR_LENGTH(TRIM(title))<6)""")
print('标题空或过短(<6字):', cur.fetchone()[0])

# 标题==源名
cur.execute("""SELECT COUNT(*) FROM announcement a JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.title=d.source_name""")
print('标题==源名:', cur.fetchone()[0])

# 待人工公告
cur.execute("""SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3""")
print('待人工(parse_status=3):', cur.fetchone()[0])

# 未解析
cur.execute("""SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0""")
print('未解析(parse_status=0):', cur.fetchone()[0])

conn.close()
