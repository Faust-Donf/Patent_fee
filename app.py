import io
import os
import re
import json
import math
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import streamlit as st
import plotly.express as px

from baiten_api import search_baiten_post
from data_utils import normalize_baiten_payload, build_dataframe, REQUIRED_COLUMNS
from fee_monitor import render_monitor_management_ui, add_fees_to_monitor

try:
    from cnipa_fee_query import query_due_fees, ensure_login_interactive
    CNIPA_AVAILABLE = True
except ImportError as e:
    CNIPA_AVAILABLE = False
    import_error_msg = str(e)
    def query_due_fees(*args, **kwargs):
        st.error(f"年费查询功能不可用，导入错误: {import_error_msg}")
        return []
    def ensure_login_interactive():
        st.error(f"年费查询功能不可用，导入错误: {import_error_msg}")
        pass
except Exception as e:
    CNIPA_AVAILABLE = False
    import_error_msg = str(e)
    def query_due_fees(*args, **kwargs):
        st.error(f"年费查询功能不可用，未知错误: {import_error_msg}")
        return []
    def ensure_login_interactive():
        st.error(f"年费查询功能不可用，未知错误: {import_error_msg}")
        pass

st.set_page_config(page_title="企南针 · 中国专利检索与监控", layout="wide")

# 固定密钥
APP_KEY = "n3krd7sx4vks2fip"
APP_SECRET = "5df54358-2885-4cde-9254-e7916cecbe69"


@st.cache_data(show_spinner=False)
def _search_and_normalize(app_key: str, app_secret: str, query: str, extra_params: Dict[str, Any]) -> Tuple[pd.DataFrame, Optional[int]]:
    safe_extra = dict(extra_params)
    try:
        ps = int(safe_extra.get("page_size", 10))
    except Exception:
        ps = 10
    safe_extra["page_size"] = min(max(ps, 1), 10)
    safe_extra["page_index"] = max(1, int(safe_extra.get("page_index", 1)))

    resp = search_baiten_post(
        app_key=app_key,
        app_secret=app_secret,
        query=query,
        page_index=safe_extra.get("page_index", 1),
        page_size=safe_extra.get("page_size", 10),
        sort_field="ad_sort",
        sort="desc",
        level="TWO",
        source=63,
        extra_params={},
    )
    if not resp.get("ok"):
        st.warning(f"检索第 {safe_extra['page_index']} 页时接口返回失败。")
        st.json(resp)
        return pd.DataFrame(columns=REQUIRED_COLUMNS), 0

    records, total_count = normalize_baiten_payload(resp["response"])
    df = build_dataframe(records)
    return df, total_count


def _inject_css():
    css_path = os.path.join("assets", "soopat.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def sidebar_controls() -> Dict[str, Any]:
    st.sidebar.header("搜索参数")
    
    max_pages_to_fetch = st.sidebar.number_input("最大获取页数", min_value=1, value=5, step=1, key="max_pages_to_fetch")
    st.sidebar.info(f"每次搜索最多返回 {max_pages_to_fetch * 10} 条专利记录 (每页10条)。")
    
    return {"extra": {"page_size": 10, "page_index": 1}, "max_pages_to_fetch": int(max_pages_to_fetch)}


def filters_ui(df: pd.DataFrame) -> Dict[str, Any]:
    st.subheader("筛选条件")
    cols = st.columns(4)
    with cols[0]:
        company = st.multiselect("公司名称", sorted([x for x in df["公司名称"].unique() if x]))
    with cols[1]:
        ptype = st.multiselect("专利类型", sorted([x for x in df["专利类型"].unique() if x]))
    with cols[2]:
        law = st.multiselect("法律状态", sorted([x for x in df["当前法律状态"].unique() if x]))
    with cols[3]:
        inventor = st.text_input("发明人包含关键词")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("申请开始日期", value=None)
    with col2:
        end_date = st.date_input("申请结束日期", value=None)

    filters = {
        "公司名称": company,
        "专利类型": ptype,
        "法律状态": law,
        "发明人关键词": inventor.strip() if inventor else "",
        "开始": str(start_date) if start_date else "",
        "结束": str(end_date) if end_date else "",
    }

    chips = []
    for k, v in filters.items():
        if isinstance(v, list) and v:
            chips.append(f'''<span class='chip'>{k}: {', '.join(v)}</span>''')
        elif isinstance(v, str) and v:
            chips.append(f'''<span class='chip'>{k}: {v}</span>''')
    if chips:
        st.markdown(f'''<div class='chips'>{''.join(chips)}</div>''', unsafe_allow_html=True)

    df_f = df.copy()
    if company:
        df_f = df_f[df_f["公司名称"].isin(company)]
    if ptype:
        df_f = df_f[df_f["专利类型"].isin(ptype)]
    if law:
        df_f = df_f[df_f["当前法律状态"].isin(law)]
    if inventor:
        df_f = df_f[df_f["发明人"].str.contains(inventor, na=False)]
    if start_date:
        df_f = df_f[(df_f["申请时间"] >= str(start_date))]
    if end_date:
        df_f = df_f[(df_f["申请时间"] <= str(end_date))]

    return {"df": df_f, "filters": filters}


def _style_table(df: pd.DataFrame):
    def color_type(val: str) -> str:
        if val == "发明": return "background-color:#e3f2fd;color:#0b61b7;"
        if val == "实用新型": return "background-color:#e8f5e9;color:#1b5e20;"
        if val == "外观设计": return "background-color:#fff3e0;color:#e65100;"
        return ""

    def color_status(val: str) -> str:
        if not isinstance(val, str): return ""
        if "有权" in val: return "background-color:#e8f5e9;color:#1b5e20;"
        if "无效" in val or "失效" in val: return "background-color:#ffebee;color:#b71c1c;"
        return ""

    styler = df.style.map(color_type, subset=["专利类型"]).map(color_status, subset=["当前法律状态"])
    return styler

def export_buttons(df: pd.DataFrame, filename: str = "专利统计.xlsx", sheet_name: str = "专利统计"):
    st.subheader("导出")
    to_cols = [c for c in REQUIRED_COLUMNS if c in df.columns]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df[to_cols].to_excel(writer, index=False, sheet_name=sheet_name)
    st.download_button(
        label="导出为 Excel",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

def dashboard(df: pd.DataFrame):
    st.subheader("仪表盘 / 可视化")
    c1, c2 = st.columns(2)
    with c1:
        if not df.empty:
            gb = df.groupby("专利类型").size().reset_index(name="数量")
            fig = px.pie(gb, names="专利类型", values="数量", title="按专利类型分布")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if not df.empty:
            gb2 = df.groupby(["公司名称", "专利类型"]).size().reset_index(name="数量")
            fig2 = px.treemap(gb2, path=["公司名称", "专利类型"], values="数量", title="公司-类型 结构树")
            st.plotly_chart(fig2, use_container_width=True)
    if not df.empty:
        df_year = df.copy()
        df_year["申请年份"] = df_year["申请时间"].str.slice(0, 4)
        gb3 = df_year.groupby("申请年份").size().reset_index(name="数量")
        fig3 = px.bar(gb3, x="申请年份", y="数量", title="按申请年份数量趋势")
        st.plotly_chart(fig3, use_container_width=True)

def _hero() -> Dict[str, Any]:
    with st.form("search_form"):
        query = st.text_input("搜索关键词", value=st.session_state.get("current_query", ""), placeholder="输入公司、申请号、专利名等关键词", label_visibility="collapsed")
        run_all = st.form_submit_button("搜索", use_container_width=True, type="primary")
    return {"query": query, "run_all": run_all}

def run_fee_query(df: pd.DataFrame, selected_indices: List[Any], storage_state: dict):
    progress_bar = st.progress(0)
    fee_results: List[Dict[str, Any]] = []
    for i, idx in enumerate(selected_indices):
        patent = df.loc[idx]
        app_no_raw = patent['专利号']
        app_no = re.sub(r'\D', '', app_no_raw)
        try:
            st.write(f"正在查询 {app_no_raw} (处理后: {app_no})...")
            fees = query_due_fees(app_no, headful=False, storage_state=storage_state)
            for fee in fees:
                fee_results.append({
                    '专利号': app_no_raw,
                    '专利名称': patent['专利名称'],
                    '公司名称': patent['公司名称'],
                    '当前法律状态': patent.get('当前法律状态', ''),
                    '费用种类': fee['费用种类'],
                    '缴费期限届满日': fee['缴费期限届满日'],
                    '金额': fee['金额']
                })
            progress_bar.progress((i + 1) / len(selected_indices))
        except Exception as e:
            st.error(f"查询 {app_no_raw} 失败：{e}")
    # 写入 session，不渲染；让上层统一展示
    st.session_state.fee_query_results = fee_results
    st.session_state.fee_query_patent_info = df.loc[selected_indices].to_dict('records') if len(selected_indices) == 1 else None
    st.session_state.fee_query_just_updated = True
    if not fee_results:
        st.session_state.fee_query_empty = True
    else:
        st.session_state.fee_query_empty = False

def fee_query_tab_content():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("年费查询")
    
    if not CNIPA_AVAILABLE:
        st.warning("年费查询功能不可用，相关依赖未能加载。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if not st.session_state.get("cnipa_login_state"):
        st.warning("您需要上传 CNIPA 登录状态文件才能查询年费。")
        with st.expander("如何获取登录状态文件 (state.json)？"):
            st.markdown("""
            1.  在您的**本地电脑**上（而不是在这个网页上）运行此应用。
            2.  在侧边栏找到“生成登录文件”按钮并点击。
            3.  程序会弹出一个浏览器窗口，请在其中手动完成登录和滑块验证。
            4.  成功登录后，程序目录下会自动生成一个 `state.json` 文件。
            5.  将这个 `state.json` 文件上传到下方即可。
            """)

        uploaded_file = st.file_uploader("上传 state.json 文件", type=["json"], accept_multiple_files=False)
        
        if uploaded_file is not None:
            try:
                state_content = json.loads(uploaded_file.getvalue().decode("utf-8"))
                if "cookies" in state_content and "origins" in state_content:
                    st.session_state.cnipa_login_state = state_content
                    st.success("登录状态文件上传成功！页面将自动刷新以应用登录状态。")
                    st.rerun()
                else:
                    st.error("文件格式不正确，请确保上传的是由本应用生成的 state.json 文件。")
            except Exception as e:
                st.error(f"读取文件失败，请确保上传的是正确的 JSON 文件。错误: {e}")

    else: # 已登录
        st.success("CNIPA 登录状态已加载，可以开始查询年费。")
        df = st.session_state.get("df_search_results")
        login_state = st.session_state.get("cnipa_login_state")
        
        if df is not None and not df.empty:
            st.write("---")
            if st.button("一键查询全部年费", type="primary", use_container_width=True):
                run_fee_query(df, df.index.tolist(), login_state)
            
            st.write("---")
            st.write("或者，选择要查询年费的专利：")
            selected_patents = st.multiselect("专利列表", options=df.index, format_func=lambda x: f"{df.loc[x, '专利名称']} ({df.loc[x, '专利号']})" )
            
            if selected_patents and st.button("查询选中专利年费"):
                run_fee_query(df, selected_patents, login_state)
            # 统一展示最近一次查询结果
            if st.session_state.get('fee_query_results') is not None:
                st.write("---")
                fee_results = st.session_state.fee_query_results
                if st.session_state.get('fee_query_empty'):
                    st.warning("未查询到任何年费信息")
                elif fee_results:
                    if st.session_state.get('fee_query_just_updated'):
                        st.success(f"查询完成，共获得 {len(fee_results)} 条年费记录")
                    fee_df = pd.DataFrame(fee_results)
                    st.dataframe(fee_df, use_container_width=True, hide_index=True)
                    export_buttons(fee_df, filename="年费查询结果.xlsx", sheet_name="年费查询结果")
                    try:
                        add_fees_to_monitor(fee_results, patent_info=(st.session_state.fee_query_patent_info[0] if st.session_state.fee_query_patent_info else None))
                    except Exception as e:
                        st.warning(f"添加监控界面渲染失败: {e}")
                st.session_state.fee_query_just_updated = False
        else:
            st.info("请先在“检索与列表”标签页中进行专利检索。")

    st.markdown("</div>", unsafe_allow_html=True)

def local_login_sidebar():
    st.sidebar.header("本地登录工具")
    if st.sidebar.button("生成登录文件 (state.json)"):
        with st.spinner("正在打开浏览器，请手动登录..."):
            try:
                ensure_login_interactive()
                st.sidebar.success("state.json 文件已生成！")
            except Exception as e:
                st.sidebar.error(f"登录失败: {e}")

def main():
    _inject_css()
    
    # Session State 初始化
    if "df_search_results" not in st.session_state:
        st.session_state.df_search_results = None
    if "cnipa_login_state" not in st.session_state:
        st.session_state.cnipa_login_state = None
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""
    if "fee_query_results" not in st.session_state:
        st.session_state.fee_query_results = []
    if "fee_query_patent_info" not in st.session_state:
        st.session_state.fee_query_patent_info = None

    local_login_sidebar()
    st.title("企南针 · 中国专利检索与监控")
    hero = _hero()
    controls = sidebar_controls()
    
    # --- 搜索逻辑 ---
    query = hero["query"]
    run_all = hero["run_all"]

    if not run_all:
        st.info("输入关键词后点击“搜索”按钮。")
    elif not query:
        st.error("请填写检索关键词。")
    else:
        st.session_state.current_query = query
        _search_and_normalize.clear()
        page_size = controls["extra"]["page_size"]
        max_pages_to_fetch = controls["max_pages_to_fetch"]

        # --- 搜索全部逻辑 (always runs now) ---
        st.session_state.df_search_results = None # Clear previous results
        all_dfs = []
        total_patents_fetched = 0
        
        progress_text = st.empty()
        progress_bar = st.progress(0)

        for page_num in range(1, max_pages_to_fetch + 1):
            progress_text.text(f"正在获取第 {page_num}/{max_pages_to_fetch} 页...")
            df_page, total_count_api = _search_and_normalize(
                app_key=APP_KEY, app_secret=APP_SECRET, query=query, 
                extra_params={"page_index": page_num, "page_size": page_size}
            )
            
            if df_page.empty:
                progress_text.text(f"第 {page_num} 页没有更多结果，停止获取。")
                break
            
            all_dfs.append(df_page)
            total_patents_fetched += len(df_page)
            progress_bar.progress(page_num / max_pages_to_fetch)
        
        final_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(columns=REQUIRED_COLUMNS)
        st.session_state.df_search_results = final_df
        progress_bar.empty()
        progress_text.empty()
        st.success(f"搜索完成！共获取到 {len(final_df)} 条专利记录。")
        if total_count_api is not None:
            st.info(f"API 报告总共有 {total_count_api} 条专利。")

    # --- 页面渲染 ---
    tabs = st.tabs(["检索与列表", "年费查询", "年费监控", "仪表盘"])
    df_from_session = st.session_state.df_search_results

    with tabs[0]:
        if df_from_session is not None:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.success(f"当前共加载 {len(df_from_session)} 条记录")
            fx = filters_ui(df_from_session)
            df_filtered = fx["df"]
            st.dataframe(_style_table(df_filtered), use_container_width=True, hide_index=True)
            export_buttons(df_filtered)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("点击搜索后将在此处显示结果。")

    with tabs[1]:
        fee_query_tab_content()

    with tabs[2]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        render_monitor_management_ui()
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        if df_from_session is not None:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            dashboard(df_from_session)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("检索数据后将显示仪表盘。")

if __name__ == "__main__":
    main()
