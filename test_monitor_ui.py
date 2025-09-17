# -*- coding: utf-8 -*-
"""
年费监控界面测试脚本
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fee_monitor import FeeMonitor, render_monitor_management_ui, add_fees_to_monitor

st.set_page_config(page_title="年费监控功能测试", layout="wide")

def create_test_data():
    """创建测试数据"""
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
            '缴费期限届满日': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            '金额': '270.00'
        },
        {
            '专利号': 'CN202110987654.5',
            '专利名称': '无线通信模块',
            '公司名称': '通信技术公司',
            '当前法律状态': '专利权无权',
            '费用种类': '发明专利第4年年费',
            '缴费期限届满日': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
            '金额': '900.00'
        }
    ]
    return test_fees

def main():
    st.title("年费监控功能测试")
    
    # 初始化监控器
    if 'fee_monitor' not in st.session_state:
        st.session_state.fee_monitor = FeeMonitor()
    
    tabs = st.tabs(["监控管理", "添加测试数据", "功能说明"])
    
    with tabs[0]:
        st.header("年费监控管理")
        render_monitor_management_ui()
    
    with tabs[1]:
        st.header("添加测试数据")
        st.write("这里可以添加一些测试数据来演示年费监控功能")
        
        test_fees = create_test_data()
        
        st.subheader("测试年费数据")
        df_test = pd.DataFrame(test_fees)
        st.dataframe(df_test, use_container_width=True, hide_index=True)
        
        st.write("---")
        add_fees_to_monitor(test_fees)
    
    with tabs[2]:
        st.header("功能说明")
        st.markdown("""
        ### 年费监控功能特点
        
        1. **紧急程度标记**：
           - ⚫ 已失效：灰色（法律状态为无权）
           - 🔴 已逾期：深红色
           - 🔴 紧急(≤1天)：红色  
           - 🟠 急迫(≤7天)：橙红色
           - 🟡 注意(≤30天)：橙色
           - 🟡 提醒(≤90天)：金色
           - 🟢 正常(>90天)：绿色
        
        2. **数据持久化**：监控数据自动保存到本地文件
        
        3. **智能排序**：按紧急程度和到期日期自动排序
        
        4. **统计信息**：实时显示各紧急程度的数量统计
        
        5. **导出功能**：支持导出监控数据为Excel格式
        
        ### 使用方法
        1. 在"添加测试数据"标签页中选择要监控的年费项
        2. 点击"添加选中项到监控"
        3. 在"监控管理"标签页中查看和管理监控项
        """)

if __name__ == "__main__":
    main()