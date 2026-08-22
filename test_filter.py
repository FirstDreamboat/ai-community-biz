# -*- coding: utf-8 -*-
"""临时脚本：测试新过滤规则对真实源的影响（用完删除）"""
import sys, io
sys.path.insert(0, 'collector')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import runner

# 模拟真实公告标题 vs 垃圾标题
test_titles = [
    "苏州市高新区智慧社区改造项目招标公告",          # 真实公告，应保留
    "苏州市公共资源交易中心",                          # 源名，应过滤
    "登录",                                            # 导航，应过滤
    "智慧社区_智慧园区_智慧楼宇-智慧城市网",            # 栏目页，应过滤
    "安防监控设备价格|型号|厂家",                      # 黄页，应过滤
    "苏州市吴中区老旧小区改造工程竞争性磋商公告",       # 真实公告，应保留
    "电子保函-招商银行",                               # 功能页，应过滤
    "苏州市轨道交通6号线工程设备采购招标公告",          # 真实公告，应保留
    "开标大厅",                                        # 功能页，应过滤
    "苏州工业园区智能化综合布线系统集成项目公开招标公告",  # 真实公告，应保留
]
print("=== 标题过滤测试 ===")
for t in test_titles:
    yellow = any(k in t for k in runner._YELLOW_PAGE_KEYWORDS)
    nav = any(k in t for k in runner._NAV_KEYWORDS)
    col = runner.is_column_page(t)
    verdict = "保留" if not (yellow or nav or col) else "过滤"
    print(f"  [{verdict}] {t}  (yellow={yellow} nav={nav} col={col})")
