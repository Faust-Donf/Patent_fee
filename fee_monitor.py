# -*- coding: utf-8 -*-
"""
年费监控模块
提供年费监控的数据存储、管理和界面功能
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st

# 监控数据存储文件
MONITOR_DATA_FILE = "fee_monitor_data.json"

class FeeMonitor:
    """年费监控管理类"""
    
    def __init__(self):
        self.data_file = MONITOR_DATA_FILE
        self.monitored_fees = self.load_monitored_fees()
    
    def load_monitored_fees(self) -> List[Dict[str, Any]]:
        """从文件加载监控的年费数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"加载监控数据失败: {e}")
                return []
        return []
    
    def save_monitored_fees(self):
        """保存监控的年费数据到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitored_fees, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存监控数据失败: {e}")
    
    def add_monitored_fee(self, fee_data: Dict[str, Any]) -> bool:
        """添加年费监控项"""
        # 检查是否已存在相同的监控项
        for existing in self.monitored_fees:
            if (existing.get('专利号') == fee_data.get('专利号') and 
                existing.get('费用种类') == fee_data.get('费用种类')):
                return False  # 已存在
        
        # 添加监控时间戳
        fee_data['添加时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.monitored_fees.append(fee_data)
        self.save_monitored_fees()
        return True
    
    def remove_monitored_fee(self, index: int) -> bool:
        """移除年费监控项"""
        if 0 <= index < len(self.monitored_fees):
            self.monitored_fees.pop(index)
            self.save_monitored_fees()
            return True
        return False
    
    def get_urgency_level(self, due_date_str: str, legal_status: str = "") -> Dict[str, Any]:
        """根据到期日期和法律状态计算紧急程度"""
        # 先基于法律状态的快速判定
        if legal_status:
            # “无权” 保持灰色（失效，不再需要缴费）
            if "无权" in legal_status:
                return {"level": "invalid", "color": "#808080", "text": "已失效", "days_left": None}
            # “已失效” 视为需关注的已逾期（使用深红色，与到期逾期一致）
            if "已失效" in legal_status:
                return {"level": "overdue", "color": "#8B0000", "text": "已逾期", "days_left": None}
        
        if not due_date_str:
            return {"level": "unknown", "color": "#808080", "text": "未知", "days_left": None}
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            today = datetime.now()
            days_left = (due_date - today).days
            
            if days_left < 0:
                return {"level": "overdue", "color": "#8B0000", "text": "已逾期", "days_left": days_left}
            elif days_left <= 1:
                return {"level": "critical", "color": "#DC143C", "text": "紧急", "days_left": days_left}
            elif days_left <= 7:
                return {"level": "urgent", "color": "#FF4500", "text": "急迫", "days_left": days_left}
            elif days_left <= 30:
                return {"level": "warning", "color": "#FF8C00", "text": "注意", "days_left": days_left}
            elif days_left <= 90:
                return {"level": "caution", "color": "#FFD700", "text": "提醒", "days_left": days_left}
            else:
                return {"level": "normal", "color": "#32CD32", "text": "正常", "days_left": days_left}
                
        except ValueError:
            return {"level": "unknown", "color": "#808080", "text": "日期格式错误", "days_left": None}
    
    def get_monitored_fees_with_urgency(self) -> List[Dict[str, Any]]:
        """获取带紧急程度标记的监控年费列表"""
        result = []
        for fee in self.monitored_fees:
            fee_copy = fee.copy()
            urgency = self.get_urgency_level(
                fee.get('缴费期限届满日', ''), 
                fee.get('当前法律状态', '')
            )
            fee_copy['urgency'] = urgency
            result.append(fee_copy)
        
        # 按紧急程度和到期日期排序
        urgency_order = {"invalid": 0, "overdue": 1, "critical": 2, "urgent": 3, "warning": 4, "caution": 5, "normal": 6, "unknown": 7}
        result.sort(key=lambda x: (
            urgency_order.get(x['urgency']['level'], 7),
            x.get('缴费期限届满日', '9999-12-31')
        ))
        
        return result

def render_fee_selection_ui(fee_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """渲染年费选择界面，返回用户选择的年费项"""
    if not fee_results:
        return []
    
    st.subheader("选择要监控的年费项")
    
    # 创建选择框
    selected_fees = []
    
    # 使用表格形式展示，让用户选择
    df = pd.DataFrame(fee_results)
    
    # 添加选择列
    selection_data = []
    for i, fee in enumerate(fee_results):
        col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
        
        with col1:
            selected = st.checkbox("选择", key=f"fee_select_{i}")
        
        with col2:
            st.write(fee.get('费用种类', ''))
        
        with col3:
            st.write(fee.get('专利号', ''))
        
        with col4:
            st.write(fee.get('缴费期限届满日', ''))
        
        with col5:
            st.write(f"¥{fee.get('金额', '')}")
        
        if selected:
            selected_fees.append(fee)
    
    return selected_fees

def render_monitor_management_ui():
    """渲染年费监控管理界面"""
    st.header("年费监控")
    
    # 初始化监控器
    if 'fee_monitor' not in st.session_state:
        st.session_state.fee_monitor = FeeMonitor()
    
    monitor = st.session_state.fee_monitor
    
    # 获取监控的年费列表
    monitored_fees = monitor.get_monitored_fees_with_urgency()
    
    if not monitored_fees:
        st.info("暂无监控的年费项目。请先在年费查询页面查询并添加监控项目。")
        return
    
    st.success(f"当前监控 {len(monitored_fees)} 个年费项目")
    
    # 统计信息
    col1, col2, col3, col4, col5 = st.columns(5)
    
    urgency_counts = {"invalid": 0, "overdue": 0, "critical": 0, "urgent": 0, "warning": 0}
    for fee in monitored_fees:
        level = fee['urgency']['level']
        if level in urgency_counts:
            urgency_counts[level] += 1
    
    with col1:
        st.metric("已失效", urgency_counts["invalid"], delta=None)
    with col2:
        st.metric("已逾期", urgency_counts["overdue"], delta=None)
    with col3:
        st.metric("紧急(≤1天)", urgency_counts["critical"], delta=None)
    with col4:
        st.metric("急迫(≤7天)", urgency_counts["urgent"], delta=None)
    with col5:
        st.metric("注意(≤30天)", urgency_counts["warning"], delta=None)
    
    st.write("---")
    
    # 监控列表
    st.subheader("监控列表")
    
    # 创建表格数据
    table_data = []
    for i, fee in enumerate(monitored_fees):
        urgency = fee['urgency']
        days_text = f"{urgency['days_left']}天" if urgency['days_left'] is not None else "未知"
        if urgency['days_left'] is not None and urgency['days_left'] < 0:
            days_text = f"逾期{abs(urgency['days_left'])}天"
        
        table_data.append({
            "序号": i + 1,
            "专利名称": fee.get('专利名称', ''),
            "专利号": fee.get('专利号', ''),
            "公司名称": fee.get('公司名称', ''),
            "费用种类": fee.get('费用种类', ''),
            "到期日期": fee.get('缴费期限届满日', ''),
            "金额": f"¥{fee.get('金额', '')}",
            "剩余天数": days_text,
            "紧急程度": urgency['text'],
            "状态颜色": urgency['color']
        })
    
    if table_data:
        df_monitor = pd.DataFrame(table_data)
        
        # 使用自定义样式显示表格
        def style_urgency(row):
            color = row['状态颜色']
            return [f'background-color: {color}; color: white; font-weight: bold' if col == '紧急程度' 
                   else '' for col in row.index]
        
        # 显示表格
        styled_df = df_monitor.drop('状态颜色', axis=1).style.apply(
            lambda row: [f'background-color: {table_data[row.name]["状态颜色"]}20' 
                        for _ in row.index], axis=1
        )
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 删除功能
        st.write("---")
        st.subheader("管理操作")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            to_remove = st.selectbox(
                "选择要删除的监控项",
                options=range(len(monitored_fees)),
                format_func=lambda x: f"{monitored_fees[x].get('专利号', '')} - {monitored_fees[x].get('费用种类', '')}",
                key="remove_select"
            )
        
        with col2:
            if st.button("删除选中项", type="secondary"):
                if monitor.remove_monitored_fee(to_remove):
                    st.success("删除成功！")
                    st.rerun()
                else:
                    st.error("删除失败！")
        
        # 导出功能
        st.write("---")
        st.subheader("导出监控数据")
        
        export_df = pd.DataFrame([
            {
                "专利名称": fee.get('专利名称', ''),
                "专利号": fee.get('专利号', ''),
                "公司名称": fee.get('公司名称', ''),
                "费用种类": fee.get('费用种类', ''),
                "到期日期": fee.get('缴费期限届满日', ''),
                "金额": fee.get('金额', ''),
                "紧急程度": fee['urgency']['text'],
                "剩余天数": fee['urgency']['days_left'],
                "添加时间": fee.get('添加时间', '')
            }
            for fee in monitored_fees
        ])
        
        # 导出按钮
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="年费监控")
        
        st.download_button(
            label="导出监控数据为 Excel",
            data=output.getvalue(),
            file_name=f"年费监控_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # 一键删除全部
        st.write("---")
        with st.expander("危险操作：批量删除"):
            st.warning("此操作将删除所有监控项，不可撤销。")
            col_a, col_b = st.columns([2,1])
            with col_a:
                confirm_text = st.text_input("输入 DELETE 以确认删除所有监控项", key="delete_all_confirm")
            with col_b:
                if st.button("删除全部", type="secondary"):
                    if confirm_text.strip() == "DELETE":
                        monitor.monitored_fees = []
                        monitor.save_monitored_fees()
                        st.success("已删除全部监控项。")
                        st.rerun()
                    else:
                        st.error("确认文本不匹配，未执行删除。")

def add_fees_to_monitor(fee_results: List[Dict[str, Any]], patent_info: Dict[str, Any] = None):
    """添加年费到监控列表的界面"""
    if not fee_results:
        return
    st.write("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("添加到年费监控")
    with col2:
        if st.button("清除查询结果", type="secondary", help="清除当前显示的年费查询结果"):
            for k in ['fee_query_results','fee_query_patent_info','monitor_fee_selected']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # 初始化监控器
    if 'fee_monitor' not in st.session_state:
        st.session_state.fee_monitor = FeeMonitor()
    monitor = st.session_state.fee_monitor

    # 初始化已选缓存
    if 'monitor_fee_selected' not in st.session_state:
        # 默认全选所有可添加项（不包含已在监控里的同专利号+费用种类组合）
        existing_keys = set()
        for m in st.session_state.fee_monitor.monitored_fees:
            existing_keys.add((m.get('专利号'), m.get('费用种类')))
        preselect = set()
        for idx, fee in enumerate(fee_results):
            key = (fee.get('专利号'), fee.get('费用种类'))
            if key not in existing_keys:
                preselect.add(idx)
        st.session_state.monitor_fee_selected = preselect

    st.markdown("<small>为避免每次勾选触发页面刷新，已改为批量选择后统一提交。</small>", unsafe_allow_html=True)

    with st.form("monitor_add_form"):
        selected_indices = []
        # 构建当前已存在监控键集合
        existing_keys_live = set((m.get('专利号'), m.get('费用种类')) for m in monitor.monitored_fees)

        for i, fee in enumerate(fee_results):
            cols = st.columns([0.6, 3, 2, 2, 1.6])
            # 复选框状态：来源于 session 缓存
            key = (fee.get('专利号'), fee.get('费用种类'))
            already_monitored = key in existing_keys_live
            default_checked = (i in st.session_state.monitor_fee_selected) and (not already_monitored)
            with cols[0]:
                if already_monitored:
                    st.checkbox("", key=f"monitor_fee_{i}", value=False, disabled=True)
                    # 保证不在选择集合
                    if i in st.session_state.monitor_fee_selected:
                        st.session_state.monitor_fee_selected.remove(i)
                    checked = False
                else:
                    checked = st.checkbox("", key=f"monitor_fee_{i}", value=default_checked)
            if checked:
                st.session_state.monitor_fee_selected.add(i)
            else:
                if i in st.session_state.monitor_fee_selected:
                    st.session_state.monitor_fee_selected.remove(i)
            with cols[1]:
                st.write(fee.get('费用种类',''))
            with cols[2]:
                st.write(fee.get('缴费期限届满日',''))
            with cols[3]:
                st.write(f"¥{fee.get('金额','')}")
            with cols[4]:
                urgency = monitor.get_urgency_level(
                    fee.get('缴费期限届满日',''),
                    fee.get('当前法律状态','')
                )
                st.markdown(f'<span style="color:{urgency["color"]};font-weight:bold">{urgency["text"]}</span>', unsafe_allow_html=True)

        submit = st.form_submit_button("添加选中项到监控", type="primary")

    if submit:
        chosen = sorted(list(st.session_state.monitor_fee_selected))
        if not chosen:
            st.warning("请至少选择一个年费项。")
            return
        added_count = 0
        duplicate_count = 0
        for idx in chosen:
            fee = fee_results[idx].copy()
            if patent_info:
                fee.update({
                    '专利名称': patent_info.get('专利名称', fee.get('专利名称', '')),
                    '公司名称': patent_info.get('公司名称', fee.get('公司名称', '')),
                })
            if monitor.add_monitored_fee(fee):
                added_count += 1
            else:
                duplicate_count += 1
        if added_count:
            st.success(f"成功添加 {added_count} 个年费项到监控！")
        if duplicate_count:
            st.info(f"有 {duplicate_count} 个年费项已存在或被忽略。")
        # 将已成功添加的索引从已选集合中移除，保留未添加的
        for idx in chosen:
            if idx in st.session_state.monitor_fee_selected:
                st.session_state.monitor_fee_selected.remove(idx)