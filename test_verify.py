# -*- coding: utf-8 -*-
"""临时脚本：测试 verify_service 相关度拦截（用完删除）"""
import sys, io
sys.path.insert(0, 'backend')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.services import verify_service

# 1. 本地相关度判定
print("=== 本地相关度 ===")
for text in [
    "医院智能化系统采购项目，含楼宇对讲、病房呼叫系统",
    "市政道路改造工程，含沥青铺设、排水管网",
    "老旧小区智慧社区改造，含可视对讲门禁系统",
    "桥梁加固工程及附属设施施工",
]:
    print(f"  {verify_service._local_relevance(text)} <- {text[:35]}")

# 2. 查看 verify_announcement 签名
import inspect
print()
print("verify_announcement 签名:", inspect.signature(verify_service.verify_announcement))
print("_local_relevance 签名:", inspect.signature(verify_service._local_relevance))
