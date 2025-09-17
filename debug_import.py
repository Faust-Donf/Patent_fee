# -*- coding: utf-8 -*-
"""
调试导入问题的脚本
"""

import sys
import traceback

print("Python版本:", sys.version)
print("当前工作目录:", sys.path[0])

print("\n=== 测试基础导入 ===")
try:
    import streamlit as st
    print("✓ Streamlit导入成功")
except Exception as e:
    print("✗ Streamlit导入失败:", e)

try:
    import playwright
    print("✓ Playwright导入成功")
except Exception as e:
    print("✗ Playwright导入失败:", e)

try:
    from playwright.async_api import async_playwright
    print("✓ Playwright async_api导入成功")
except Exception as e:
    print("✗ Playwright async_api导入失败:", e)

print("\n=== 测试CNIPA模块导入 ===")
try:
    import cnipa_fee_query
    print("✓ cnipa_fee_query模块导入成功")
except Exception as e:
    print("✗ cnipa_fee_query模块导入失败:", e)
    traceback.print_exc()

try:
    from cnipa_fee_query import query_due_fees, ensure_login_interactive
    print("✓ CNIPA函数导入成功")
except Exception as e:
    print("✗ CNIPA函数导入失败:", e)
    traceback.print_exc()

print("\n=== 模拟app.py中的导入逻辑 ===")
try:
    from cnipa_fee_query import query_due_fees, ensure_login_interactive
    CNIPA_AVAILABLE = True
    print("✓ CNIPA_AVAILABLE = True")
except ImportError as e:
    CNIPA_AVAILABLE = False
    print("✗ CNIPA_AVAILABLE = False, 错误:", e)
    traceback.print_exc()

print(f"\n最终结果: CNIPA_AVAILABLE = {CNIPA_AVAILABLE}")