# 专利检索与监控（Streamlit）

功能概览：
- 专利统计列表字段：公司名称、专利名称、专利类型、专利号、申请时间、授权时间、发明人、当前法律状态、最临近的一次缴纳年费截止日期。
- 筛选：公司名称、专利类型、法律状态、发明人关键词、申请日期区间。
- 导出：一键导出 Excel（.xlsx）。
- 仪表盘：按专利类型分布饼图、公司-类型结构树（Treemap）、按申请年份数量趋势柱状图。
- 智能检索：集成佰腾接口调用（需提供 App Key/Secret）。

## 快速开始

1. 安装依赖（建议使用虚拟环境）：
```bash
pip install -r requirements.txt
```

2. 运行：
```bash
streamlit run app.py
```

3. 在左侧填写 `App Key` 与 `App Secret`，输入公司或关键词，点击“开始检索”。

> 也可通过环境变量提供：
- `BAITEN_APP_KEY`
- `BAITEN_APP_SECRET`

## 代码结构
- `app.py`：Streamlit UI（检索、筛选、导出、可视化）。
- `baiten_api.py`：佰腾搜索 API 客户端与签名逻辑。
- `data_utils.py`：结果规范化与 DataFrame 构建。
- `requirements.txt`：依赖清单。

## 注意
- 佰腾接口的字段名可能与示例不同，`data_utils.normalize_baiten_item` 中已做多候选字段映射，可按实际返回调整。
- 签名规则按提供信息采用 `md5("2025" + len(query) + app_secret)`，并自动尝试 UTF-8/GBK × 小写/大写四种组合；若接入失败，请根据实际开放平台文档修正。
