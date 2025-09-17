# -*- coding: utf-8 -*-
"""
CNIPA 年费查询后端模块（Playwright）
对外函数：
  - ensure_login_interactive()
  - query_due_fees(app_no: str, headful: bool = True) -> list[dict]
  - has_login_state() -> bool
"""

# ---- Windows: 事件循环策略（Playwright 需要子进程支持）----
import sys, asyncio
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import os, time, re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from getpass import getpass
from playwright.async_api import async_playwright, TimeoutError as PWTimeout, Page, Locator

# ------- 基础配置 -------
ROOTS = [
    "https://interactive.cponline.cnipa.gov.cn/od/public/index",
    "https://interactive.cponline.cnipa.gov.cn/od/public",
    "https://interactive.cponline.cnipa.gov.cn/od",
]
BASE = Path(__file__).parent
STATE_FILE = BASE / "state.json"

# ------- 选择器 -------
MENU_PAY = ['text=缴费服务','a:has-text("缴费服务")','button:has-text("缴费服务")','text=/缴费\\s*服务/']
MENU_FEE = ['text=费用查询','a:has-text("费用查询")','button:has-text("费用查询")']
TAB_DUE  = ['text=应缴费查询','a:has-text("应缴费查询")','button:has-text("应缴费查询")']

INPUTS = [
    'input[placeholder*="申请号/专利号"]',
    'input[placeholder*="请输入申请号/专利号"]',
    'input[placeholder*="申请号"]',
    'input[aria-label*="申请"]',
    'input[name*="application" i]',
    'input[id*="application" i]',
    'input[type="text"]',
]
QUERY_BTNS = [
    'button:has-text("查询")',
    'text=查询',
    'role=button[name=/查询|Search/i]',
]
DISMISS = [
    'button:has-text("我知道了")','button:has-text("同意")','button:has-text("关闭")',
    'text=我知道了','text=关 闭',
]

# ------- 工具函数（仅被内部调用，顶层不执行）-------
async def _try_click(scope, sels, timeout=1200) -> bool:
    for s in sels:
        try:
            loc = scope.locator(s).first
            if await loc.is_visible(timeout=timeout):
                await loc.click(timeout=timeout)
                return True
        except Exception:
            pass
    return False

async def _open_roots(page: Page):
    for url in ROOTS:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass
            html = await page.content()
            if "<html" in html.lower():
                return True
        except Exception:
            continue
    return False

async def _goto_fee_query(page: Page) -> bool:
    ok = await _try_click(page, MENU_PAY)
    if not ok:
        for fr in page.frames:
            if await _try_click(fr, MENU_PAY):
                ok = True; break
    if not ok: return False
    await page.wait_for_timeout(600)

    ok2 = await _try_click(page, MENU_FEE)
    if not ok2:
        for fr in page.frames:
            if await _try_click(fr, MENU_FEE):
                ok2 = True; break
    if not ok2: return False

    # 可选"应缴费查询"
    try:
        if await page.locator('text=应缴费查询').first.is_visible(timeout=1200):
            if not await _try_click(page, TAB_DUE):
                for fr in page.frames:
                    if await _try_click(fr, TAB_DUE):
                        break
    except Exception:
        pass
    return True

async def _wait_find_input_and_button(page: Page, total_ms: int = 20000) -> Tuple[Locator, Optional[Locator]]:
    deadline = time.time() + total_ms/1000.0
    while time.time() < deadline:
        scopes = [page] + list(page.frames)
        for scope in scopes:
            # 输入框
            inp = None
            for s in INPUTS:
                try:
                    cand = scope.locator(s).first
                    if await cand.is_visible(timeout=250):
                        inp = cand; break
                except Exception:
                    continue
            if not inp: 
                continue
            # 查询按钮（优先就近）
            btn = None
            try:
                near_btn = inp.locator(
                    'xpath=ancestor::*[self::form or contains(@class,"form") or contains(@class,"search")][1]'
                    '//button[contains(.,"查询")]'
                ).first
                if await near_btn.is_visible(timeout=250):
                    btn = near_btn
            except Exception:
                pass
            if not btn:
                for s in QUERY_BTNS:
                    try:
                        candb = scope.locator(s).first
                        if await candb.is_visible(timeout=250):
                            btn = candb; break
                    except Exception:
                        continue
            return inp, btn
        await page.wait_for_timeout(350)
    raise TimeoutError("等待输入框/查询按钮超时（~20s）")

async def _extract_fee_rows(page) -> list[dict]:
    """
    先尝试按标准表格解析；若表头/行不规整，则退回到全文正则扫描：
    匹配形如「实用新型专利第3年年费 2026-09-02 90.00」的三元组。
    """
    import re

    # --- 尝试 1：按表头解析 ---
    tables = await page.eval_on_selector_all(
        "table",
        """(nodes) => nodes.map(t =>
            Array.from(t.querySelectorAll('tr')).map(tr =>
                Array.from(tr.querySelectorAll('th,td')).map(td => td.innerText.trim())
            )
        )"""
    )
    items = []

    def map_by_header(rows):
        # 找包含【金额】且包含【缴费期限/届满】的那一行当表头
        hdr_idx = None
        for i in range(min(3, len(rows))):
            joined = " ".join(rows[i])
            if "金额" in joined and ("缴费期限" in joined or "届满" in joined):
                hdr_idx = i; break
        if hdr_idx is None:
            return []

        header = rows[hdr_idx]
        def find_col(keys):
            for j, h in enumerate(header):
                if any(k in h for k in keys): return j
            return None

        c_type = find_col(["费用","种类"])
        c_date = find_col(["缴费期限","届满"])
        c_amt  = find_col(["金额"])
        if c_type is None or c_amt is None:
            return []

        out = []
        for r in rows[hdr_idx+1:]:
            if len(r) <= max(c_type, c_date or 0, c_amt): 
                continue
            t = r[c_type].strip()
            d = r[c_date].strip() if c_date is not None else ""
            a = r[c_amt].strip()
            # 只保留包含"年费/滞纳金"的行，避免把序号/占位行带进来
            if not t or (("年费" not in t) and ("滞纳金" not in t)):
                continue
            out.append({"费用种类": t, "缴费期限届满日": d, "金额": a})
        return out

    for rows in tables:
        items.extend(map_by_header(rows))

    # 若表格解析成功就去重返回
    if items:
        uniq, seen = [], set()
        for it in items:
            k = (it["费用种类"], it.get("缴费期限届满日",""), it["金额"])
            if k not in seen:
                seen.add(k); uniq.append(it)
        return uniq

    # --- 尝试 2：全文正则扫描（针对你出现的"首行粘一起"情况） ---
    text = (await page.inner_text("body")).replace("\xa0"," ").replace("\u3000"," ")
    # 匹配：费用种类（以"年费/滞纳金"结尾） + 日期 + 金额
    pat = re.compile(
        r'(?P<type>[\u4e00-\u9fa5A-Za-z0-9（）()第\-·]+?(?:年费(?:滞纳金)?))\s+'
        r'(?P<date>\d{4}-\d{2}-\d{2})\s+'
        r'(?P<amt>\d+(?:\.\d{1,2})?)'
    )
    found = []
    for m in pat.finditer(text):
        found.append({
            "费用种类": m.group("type").strip(),
            "缴费期限届满日": m.group("date"),
            "金额": m.group("amt"),
        })

    # 去重并返回
    uniq, seen = [], set()
    for it in found:
        k = (it["费用种类"], it["缴费期限届满日"], it["金额"])
        if k not in seen:
            seen.add(k); uniq.append(it)
    return uniq


# ------- 对外函数（供 streamlit_app 调用）-------
async def _ensure_login_async():
    from playwright.async_api import async_playwright
    user = os.getenv("CNIPA_USER") or input("账号(手机号/证件号): ").strip()
    pwd  = os.getenv("CNIPA_PASS") or getpass("密码: ").strip()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(locale="zh-CN")
        page = await ctx.new_page()
        if not await _open_roots(page):
            raise RuntimeError("无法打开入口页")
        print("请在弹出页面完成登录与滑块，进入首页后等待几秒…")
        await page.wait_for_function("() => !document.body.innerText.includes('登录')", timeout=120000)
        await ctx.storage_state(path=str(STATE_FILE))
        print(f"登录状态已保存到 {STATE_FILE}")
        await browser.close()

def ensure_login_interactive():
    asyncio.run(_ensure_login_async())

async def _query_due_fees_async(app_no: str, headful: bool, storage_state: Optional[dict] = None) -> List[Dict]:
    from playwright.async_api import async_playwright
    
    # 如果没有传入 state，则尝试从 state.json 文件加载
    if storage_state is None:
        if not STATE_FILE.exists():
            raise RuntimeError("未找到登录状态文件 (state.json)。")
        state_to_use = str(STATE_FILE)
    else:
        state_to_use = storage_state

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headful)
        ctx = await browser.new_context(
            locale="zh-CN",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
            viewport={"width": 1366, "height": 900},
            storage_state=state_to_use
        )
        page = await ctx.new_page()
        page.set_default_timeout(45000)

        # 入口与登录态检查
        if not await _open_roots(page):
            await browser.close()
            raise RuntimeError("无法打开入口页")
        
        body_text = await page.inner_text("body")
        if "登录" in body_text and "退出" not in body_text:
            await browser.close()
            raise RuntimeError("登录态失效，请重新生成 state.json 文件并上传。")

        # 导航到费用查询
        if not await _goto_fee_query(page):
            await browser.close()
            raise RuntimeError("未找到【缴费服务/费用查询】入口。")

        # 定位输入框+按钮
        inp, btn = await _wait_find_input_and_button(page, total_ms=20000)

        # 提交查询
        await inp.click()
        await inp.fill(app_no)
        try:
            await inp.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        if btn:
            try:
                await btn.click()
            except Exception:
                pass

        # 等待结果或暂无数据
        try:
            await page.wait_for_selector("table, .el-table, .ant-table, #cp_result_table", state="visible", timeout=20000)
        except PWTimeout:
            try:
                await page.get_by_text("暂无数据").first.wait_for(timeout=5000)
            except PWTimeout:
                pass

        rows = await _extract_fee_rows(page)
        if not rows:  # 兜底再等一下
            await page.wait_for_timeout(2000)
            rows = await _extract_fee_rows(page)

        await browser.close()
        return rows

def query_due_fees(app_no: str, headful: bool = True, storage_state: Optional[dict] = None) -> List[Dict]:
    """返回 [{'费用种类':..., '缴费期限届满日':..., '金额':...}, ...]"""
    return asyncio.run(_query_due_fees_async(app_no, headful=headful, storage_state=storage_state))

def has_login_state() -> bool:
    return STATE_FILE.exists()
