# -*- coding: utf-8 -*-
"""
测试"已失效"状态功能
"""

from fee_monitor import FeeMonitor
from datetime import datetime, timedelta

def test_invalid_status():
    """测试已失效状态的识别"""
    print("测试已失效状态功能...")
    
    monitor = FeeMonitor()
    
    # 测试不同法律状态的紧急程度计算
    test_cases = [
        {
            'name': '正常专利权维持',
            'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'legal_status': '专利权维持',
            'expected': 'urgent'
        },
        {
            'name': '专利权无权',
            'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'legal_status': '专利权无权',
            'expected': 'invalid'
        },
        {
            'name': '专利权终止无权',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'legal_status': '专利权终止无权',
            'expected': 'invalid'
        },
        {
            'name': '空法律状态',
            'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'legal_status': '',
            'expected': 'urgent'
        }
    ]
    
    print("\n紧急程度计算测试:")
    for case in test_cases:
        urgency = monitor.get_urgency_level(case['due_date'], case['legal_status'])
        result = "✓" if urgency['level'] == case['expected'] else "✗"
        print(f"  {result} {case['name']}: {urgency['text']} (期望: {case['expected']}, 实际: {urgency['level']})")
    
    # 测试完整的监控数据
    print("\n完整监控数据测试:")
    test_fee = {
        '专利号': 'CN202110999999.9',
        '专利名称': '测试失效专利',
        '公司名称': '测试公司',
        '当前法律状态': '专利权无权',
        '费用种类': '发明专利第3年年费',
        '缴费期限届满日': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        '金额': '270.00'
    }
    
    # 添加到监控
    result = monitor.add_monitored_fee(test_fee)
    print(f"  添加失效专利到监控: {'成功' if result else '失败'}")
    
    # 获取带紧急程度的监控列表
    monitored_fees = monitor.get_monitored_fees_with_urgency()
    for fee in monitored_fees:
        if fee['专利号'] == 'CN202110999999.9':
            urgency = fee['urgency']
            print(f"  失效专利状态: {urgency['text']} (颜色: {urgency['color']})")
            break
    
    print("\n已失效状态测试完成！")

if __name__ == "__main__":
    test_invalid_status()