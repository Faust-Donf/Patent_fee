# -*- coding: utf-8 -*-
"""简单验证 CNIPA state.json 结构的脚本
用法：
    python verify_state.py /path/to/state.json
返回码：0 结构基本正确；非0 代表问题。
"""
import json, sys, os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("用法: python verify_state.py state.json")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"文件不存在: {p}")
        return 3
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"JSON 解析失败: {e}")
        return 4
    # 基础字段判断
    if not isinstance(data, dict):
        print("结构错误：根应为对象")
        return 5
    miss = []
    for k in ["cookies", "origins"]:
        if k not in data:
            miss.append(k)
    if miss:
        print(f"缺少关键字段: {miss}")
        return 6
    if not isinstance(data['cookies'], list) or not data['cookies']:
        print("cookies 列表为空或不是数组，可能无效。")
    else:
        domains = {c.get('domain') for c in data['cookies'] if isinstance(c, dict)}
        print(f"包含 {len(data['cookies'])} 条 cookie，域: {', '.join(sorted(d for d in domains if d))}")
    print("结构检测完成。")
    return 0

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
