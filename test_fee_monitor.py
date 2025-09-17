# -*- coding: utf-8 -*-
"""
年费监控功能测试脚本
"""

import json
from datetime import datetime, timedelta
from fee_monitor import FeeMonitor

def test_fee_monitor():
    """测试年费监控功能"""
    print("开始测试年费监控功能...")
    
    # 创建监控器实例
    monitor = FeeMonitor()
    
    # 创建测试数据
    test_fees = [
        {
            '专利号': 'CN202110123456.7',
            '专利名称': '一种智能控制系统',
            '公司名称': '测试科技有限公司',
            '当前法律状态': '专利权维持',
            '费用种类': '发明专利第3年年费',
            '缴费期限届满日': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            '金额': '270.00'
        },
        {
            '专利号': 'CN202110654321.2',
            '专利名称': '新型传感器装置',
            '公司名称': '创新技术公司',
            '当前法律状态': '专利权维持',
            '费用种类': '实用新型专利第2年年费',
            '缴费期限届满日': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            '金额': '150.00'
        },
        {
            '专利号': 'CN202110789012.1',
            '专利名称': '智能家居控制面板',
            '公司名称': '智能家居公司',
            '当前法律状态': '专利权无权',
            '费用种类': '发明专利第5年年费',
            '缴费期限届满日': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
            '金额': '1200.00'
        },
        {
            '专利号': 'CN202110456789.3',
            '专利名称': '自动化生产线控制器',
            '公司名称': '工业自动化公司',
            '当前法律状态': '专利权维持',
            '费用种类': '发明专利第2年年费',
            '缴费期限届满日': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
            '金额': '270.00'
        }
    ]
    
    # 测试添加监控项
    print("\n1. 测试添加监控项...")
    for i, fee in enumerate(test_fees):
        result = monitor.add_monitored_fee(fee)
        print(f"   添加第{i+1}个监控项: {'成功' if result else '失败'}")
    
    # 测试重复添加
    print("\n2. 测试重复添加...")
    result = monitor.add_monitored_fee(test_fees[0])
    print(f"   重复添加第1个监控项: {'成功' if result else '失败（预期）'}")
    
    # 测试获取带紧急程度的监控列表
    print("\n3. 测试紧急程度计算...")
    monitored_fees = monitor.get_monitored_fees_with_urgency()
    for fee in monitored_fees:
        urgency = fee['urgency']
        print(f"   {fee['专利号']}: {urgency['text']} ({urgency['days_left']}天)")
    
    # 测试紧急程度分类
    print("\n4. 测试紧急程度分类...")
    urgency_counts = {}
    for fee in monitored_fees:
        level = fee['urgency']['level']
        urgency_counts[level] = urgency_counts.get(level, 0) + 1
    
    for level, count in urgency_counts.items():
        print(f"   {level}: {count}个")
    
    # 测试删除监控项
    print("\n5. 测试删除监控项...")
    if len(monitored_fees) > 0:
        result = monitor.remove_monitored_fee(0)
        print(f"   删除第1个监控项: {'成功' if result else '失败'}")
        print(f"   剩余监控项数量: {len(monitor.monitored_fees)}")
    
    print("\n年费监控功能测试完成！")

if __name__ == "__main__":
    test_fee_monitor()