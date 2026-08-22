# -*- coding: utf-8 -*-
"""临时脚本：第四轮清理——待人工/未解析中的栏目页功能页公告（用完删除）"""
import pymysql, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(host='127.0.0.1', port=3306, user='opportunity',
                       password='opportunity123', database='opportunity_system',
                       charset='utf8mb4')
cur = conn.cursor()

PORTAL = ['开标大厅', '电子保函', '专家库', '交易系统', '信息库', '经营主体',
          '统一身份认证', '监管平台', '不见面开标', '报表', '征集', '目录',
          '培训系统', '信用信息', '主体信息', '政务动态', '年度工作报表',
          '回信', '调查征集', '建议咨询', '申请获取', '加载中', '公示信息',
          '能力评价', '企业入会', '企业服务中心', '会员动态', '协会要闻',
          '专家抽取', '不见面', '招标投标监管', '法规规章', '下载专区',
          '视频中心', '专题专栏', '政策解读', '数据开放', '数字证书']

# 栏目页特征：以「-XX中心/平台/网/集团/公司/局/协会」结尾
col_re = re.compile(r'-(?:[\u4e00-\u9fa5]{2,20}(?:交易中心|交易平台|政务服务中心|中心|平台|集团|公司|局|协会|委员会|管委会|厅|部|院|所))$')
sep_re = re.compile(r'[_\uFF5C|]')

cur.execute("SELECT id,title FROM announcement WHERE deleted=0 AND "
            "(parse_status=0 OR parse_status=3)")
rows = cur.fetchall()
ids = []
for aid, t in rows:
    t = (t or '').strip()
    if any(k in t for k in PORTAL) or col_re.search(t) or sep_re.search(t):
        ids.append(aid)
if ids:
    cur.executemany("UPDATE announcement SET deleted=1, updated_at=NOW() WHERE id=%s",
                    [(i,) for i in ids])
print('栏目/功能页公告软删:', len(ids))
conn.commit()

cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=0")
print('剩余未解析:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM announcement WHERE deleted=0 AND parse_status=3")
print('剩余待人工:', cur.fetchone()[0])
cur.execute("""SELECT a.id, a.title, d.source_name FROM announcement a
  JOIN data_source d ON a.source_id=d.id
  WHERE a.deleted=0 AND a.parse_status IN (0,3) ORDER BY a.id LIMIT 40""")
print('剩余待处理公告:')
for r in cur.fetchall():
    print(' ', r[0], '|', str(r[1])[:70], '|', r[2])
conn.close()
