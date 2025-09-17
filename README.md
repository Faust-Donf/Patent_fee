# 中国专利检索与年费监控平台

**项目链接:**
- **GitHub 仓库:** [https://github.com/Faust-Donf/Patent_fee.git](https://github.com/Faust-Donf/Patent_fee.git)
- **在线应用:** `[请在此处替换为您的 Streamlit 应用链接]`

---

### 项目简介

这是一个独立的 Web 应用，旨在为用户提供一站式的中国专利信息检索、筛选、可视化分析及年费查询功能。项目通过整合第三方 API 和 Web 自动化技术，解决了专利信息分散、年费查询繁琐的问题。

### 核心功能

- **专利检索系统:** 对接第三方专利 API，实现基于关键词的中国专利数据实时检索与展示。

- **年费智能查询:** 利用 Playwright 自动化爬取国家知识产权局（CNIPA）网站，实现精确、自动化的专利年费状态查询。通过对专利号进行预处理，有效提高了查询成功率。

- **交互式数据看板:** 使用 Streamlit 构建动态用户界面，支持多维度数据筛选（如公司、专利类型、法律状态等），并通过 Plotly 生成交互式图表（如饼图、树状图、条形图）进行数据可视化。

- **状态保持与优化:** 通过 Streamlit 的 `session_state` 机制，优化应用交互逻辑，确保在多标签页切换时用户的检索结果得以保留，显著提升了用户体验。

- **便捷操作:** 实现“一键查询全部”功能，批量处理检索到的所有专利；支持将筛选后的数据和年费查询结果一键导出为 Excel 文件。

### 技术栈

- **后端/核心:** Python
- **前端/UI:** Streamlit
- **数据处理与分析:** Pandas, NumPy
- **Web 自动化与爬虫:** Playwright
- **数据可视化:** Plotly
- **API 交互:** Requests
- **版本控制与部署:** Git, GitHub, Streamlit Community Cloud
 - **版本控制与部署:** Git, GitHub, Streamlit Community Cloud

---

## 部署指南（Ubuntu 简要版）

### 1. 环境准备
```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3 python3-venv python3-pip git curl build-essential
```

### 2. 获取代码 & 安装依赖
```bash
git clone https://github.com/Faust-Donf/Patent_fee.git
cd Patent_fee
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. 准备 CNIPA 登录状态文件 `state.json`
在本地通过交互式登录生成后上传。也可以通过环境变量指定路径：
```bash
export CNIPA_STATE_FILE=/opt/patent_fee/state/state.json
```
权限建议：
```bash
chmod 600 state.json
```

### 4. 运行应用
```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

### 5. systemd 示例
`/etc/systemd/system/patent_fee.service`
```
[Unit]
Description=Patent Fee Streamlit
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/patent_fee
Environment=CNIPA_STATE_FILE=/opt/patent_fee/state/state.json
Environment=PATH=/opt/patent_fee/.venv/bin
ExecStart=/opt/patent_fee/.venv/bin/streamlit run app.py --server.address=0.0.0.0 --server.port=8501
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now patent_fee
```

### 6. 验证 `state.json`
```bash
python verify_state.py /path/to/state.json
```

### 7. Nginx 反向代理（可选）
```nginx
server {
	listen 80;
	server_name your.domain.com;
	location / { proxy_pass http://127.0.0.1:8501/; }
}
```

### 8. 关键环境变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| CNIPA_STATE_FILE | 指定 state.json 路径 | /opt/patent_fee/state/state.json |
| CNIPA_USER / CNIPA_PASS | 自动脚本生成 state.json 时使用（可选） | 138*****/secret |

---