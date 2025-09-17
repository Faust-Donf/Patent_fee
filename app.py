import io
import os
import re
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
import plotly.express as px

from baiten_api import search_baiten_post
from data_utils import normalize_baiten_payload, build_dataframe, REQUIRED_COLUMNS
try:
    from cnipa_fee_query import query_due_fees, has_login_state, ensure_login_interactive
    CNIPA_AVAILABLE = True
except ImportError:
    CNIPA_AVAILABLE = False
    def query_due_fees(*args, **kwargs):
        st.error("Playwright-related function not available.")
        return []
    def has_login_state():
        return False
    def ensure_login_interactive():
        st.error("Playwright-related function not available.")
        pass

st.set_page_config(page_title="企南针 · 中国专利检索与监控", layout="wide")

# 固定密钥（根据你的要求写死在代码中）
APP_KEY = "n3krd7sx4vks2fip"
APP_SECRET = "5df54358-2885-4cde-9254-e7916cecbe69"


@st.cache_data(show_spinner=False)
def _search_and_normalize(app_key: str, app_secret: str, query: str, extra_params: Dict[str, Any]) -> pd.DataFrame:
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
		  st.warning("检索接口返回失败，已显示空结果。详情见下方调试信息。")
		  st.json(resp)
		  return pd.DataFrame(columns=REQUIRED_COLUMNS)

	 records = normalize_baiten_payload(resp["response"]) or []
	 df = build_dataframe(records)
	 return df


def _inject_css():
	 css_path = os.path.join("assets", "soopat.css")
	 if os.path.exists(css_path):
		  with open(css_path, "r", encoding="utf-8") as f:
			   st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def sidebar_controls() -> Dict[str, Any]:
	 st.sidebar.header("参数")
	 # 仅保留页码与每页条数
	 page_size = st.sidebar.number_input("每页条数 (≤10)", min_value=1, max_value=10, value=10, step=1)
	 page_index = st.sidebar.number_input("页码", min_value=1, value=1, step=1)
	 return {"extra": {"page_size": int(page_size), "page_index": int(page_index)}}

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
		  if val == "发明":
			   return "background-color:#e3f2fd;color:#0b61b7;"
		  if val == "实用新型":
			   return "background-color:#e8f5e9;color:#1b5e20;"
		  if val == "外观设计":
			   return "background-color:#fff3e0;color:#e65100;"
		  return ""

	 def color_status(val: str) -> str:
		  if not isinstance(val, str):
			   return ""
		  if "有权" in val:
			   return "background-color:#e8f5e9;color:#1b5e20;"
		  if "无效" in val or "失效" in val:
			   return "background-color:#ffebee;color:#b71c1c;"
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

def _navbar():
	 st.markdown(
		  '''
		  <div class="navbar">
			   <div style="display:flex;justify-content:space-between;align-items:center;">
					<div class="brand">企南针 · 中国专利检索</div>
					<div class="nav-links">
						 <a href="#">中国专利</a>
						 <a href="#">IPC分类</a>
					</div>
			   </div>
		  </div>
		  ''',
		  unsafe_allow_html=True,
	 )

def _hero() -> Dict[str, Any]:
	 st.markdown(
		  '''
		  <div class="hero">
			   <div class="hero-title">企南针 - 中国专利查询</div>
			   <div class="hero-subtitle">专注中国专利 · 支持检索、筛选、导出与监控</div>
		  </div>
		  ''',
		  unsafe_allow_html=True,
	 )
	 with st.form("search_form"):
		  col1, col2 = st.columns([8, 2])
		  with col1:
			   query = st.text_input("搜索关键词", value="", placeholder="输入公司、申请号、专利名等关键词", label_visibility="collapsed")
		  with col2:
			   run = st.form_submit_button("搜索", use_container_width=True)
	 return {"query": query, "run": run}

def _footer():
	 st.markdown(
		  '''
		  <div class="footer">Copyright © 2025 企南针 · 中国专利检索</div>
		  ''',
		  unsafe_allow_html=True,
	 )

def run_fee_query(df: pd.DataFrame, selected_indices: List[Any]):
    progress_bar = st.progress(0)
    fee_results = []
    
    for i, idx in enumerate(selected_indices):
        patent = df.loc[idx]
        app_no_raw = patent['专利号']
        app_no = re.sub(r'\D', '', app_no_raw)
        
        try:
            st.write(f"正在查询 {app_no_raw} (处理后: {app_no})...")
            fees = query_due_fees(app_no, headful=False)
            
            for fee in fees:
                fee_results.append({
                    '专利号': app_no_raw,
                    '专利名称': patent['专利名称'],
                    '公司名称': patent['公司名称'],
                    '费用种类': fee['费用种类'],
                    '缴费期限届满日': fee['缴费期限届满日'],
                    '金额': fee['金额']
                })
            
            progress_bar.progress((i + 1) / len(selected_indices))
        except Exception as e:
            st.error(f"查询 {app_no_raw} 失败：{e}")
    
    if fee_results:
        st.success(f"查询完成，共获得 {len(fee_results)} 条年费记录")
        fee_df = pd.DataFrame(fee_results)
        st.dataframe(fee_df, use_container_width=True, hide_index=True)
        
        export_buttons(fee_df, filename="年费查询结果.xlsx", sheet_name="年费查询结果")
    else:
        st.warning("未查询到任何年费信息")

def fee_query_tab_content():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("年费查询")
    
    if not CNIPA_AVAILABLE:
        st.warning("年费查询功能需要安装 playwright 依赖。请运行：")
        st.code("pip install playwright\nplaywright install chromium", language="bash")
        st.info("安装完成后重启应用即可使用年费查询功能。")
    else:
        # 检查登录状态
        if not has_login_state():
            st.warning("请先登录国家知识产权局账号")
            if st.button("登录 CNIPA", type="primary"):
                try:
                    ensure_login_interactive()
                    st.success("登录成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"登录失败：{e}")
        else:
            st.success("已登录 CNIPA")
            
            df = st.session_state.get("df_search_results")
            
            if df is not None and not df.empty:
                st.write("---")
                
                # 一键查询全部
                if st.button("一键查询全部年费", type="primary", use_container_width=True):
                    run_fee_query(df, df.index.tolist())
                
                st.write("---")
                
                # 选择查询
                st.write("或者，选择要查询年费的专利：")
                selected_patents = st.multiselect(
                    "专利列表",
                    options=df.index,
                    format_func=lambda x: f"{df.loc[x, '专利名称']} ({df.loc[x, '专利号']})"
                )
                
                if selected_patents and st.button("查询选中专利年费"):
                    run_fee_query(df, selected_patents)

            else:
                st.info("请先在“检索与列表”标签页中进行专利检索。")

    st.markdown("</div>", unsafe_allow_html=True)

def main():
    _inject_css()
    _navbar()
    hero = _hero()
    controls = sidebar_controls()

    # 初始化 session_state
    if "df_search_results" not in st.session_state:
        st.session_state.df_search_results = None

    tabs = st.tabs(["检索与列表", "年费查询", "仪表盘"])

    # 如果点击了搜索按钮，则执行搜索并更新 session_state
    if hero["run"]:
        _search_and_normalize.clear()
        if not hero["query"]:
            st.error("请填写 检索关键词。")
            st.stop()
        
        df = _search_and_normalize(
            app_key=APP_KEY,
            app_secret=APP_SECRET,
            query=hero["query"],
            extra_params=controls["extra"],
        )
        st.session_state.df_search_results = df
    
    # 从 session_state 获取数据
    df_from_session = st.session_state.df_search_results

    with tabs[0]: # 检索与列表
        if df_from_session is not None:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.success(f"共获得 {len(df_from_session)} 条记录")
            fx = filters_ui(df_from_session)
            df_filtered = fx["df"]
            st.dataframe(_style_table(df_filtered), use_container_width=True, hide_index=True)
            export_buttons(df_filtered)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("输入关键词后点击 ‘搜索’ 以加载数据。")

    with tabs[1]: # 年费查询
        fee_query_tab_content()

    with tabs[2]: # 仪表盘
        if df_from_session is not None:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            dashboard(df_from_session)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("检索数据后将显示仪表盘。")

    _footer()


if __name__ == "__main__":
	 main()