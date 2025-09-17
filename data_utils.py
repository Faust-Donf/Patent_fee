from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime


REQUIRED_COLUMNS = [
    "公司名称",
    "专利名称",
    "专利类型",
    "专利号",
    "申请时间",
    "授权时间",
    "发明人",
    "当前法律状态",
    "最临近的一次缴纳年费截止日期",
]


_TYPE_MAP = {
    "cn_in": "发明",
    "cn_um": "实用新型",
    "cn_dm": "外观设计",
}


def _safe_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            d = datetime.strptime(str(value).strip(), fmt)
            return d.strftime("%Y-%m-%d")
        except Exception:
            continue
    return str(value)


def _map_type(type_field: Any) -> Optional[str]:
    # type may be list like ["cn_in", "cn_gp"]
    if isinstance(type_field, list):
        for t in type_field:
            lbl = _TYPE_MAP.get(str(t).lower())
            if lbl:
                return lbl
        return ",".join(type_field)
    if isinstance(type_field, str):
        return _TYPE_MAP.get(type_field.lower(), type_field)
    return None


def normalize_baiten_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single record from Baiten API to required schema.

    Supports both flat fields and nested under 'field_values'.
    """
    src = item
    if isinstance(item.get("field_values"), dict):
        src = item["field_values"]

    company = src.get("pa") or src.get("applicant_name") or src.get("申请人")
    inventors = src.get("in") or src.get("inventor") or src.get("发明人")

    # Normalize list-like fields
    if isinstance(company, list):
        company = ", ".join([str(x) for x in company if x])
    if isinstance(inventors, list):
        inventors = ", ".join([str(x) for x in inventors if x])

    patent_type = _map_type(src.get("type") or src.get("patent_type") or src.get("类型"))

    return {
        "公司名称": company or "",
        "专利名称": src.get("ti") or src.get("title") or src.get("专利名称") or "",
        # 按常见理解，这里将专利号取申请号 an；如需改为公开/授权号可换为 pn
        "专利类型": patent_type or "",
        "专利号": src.get("an") or src.get("application_number") or src.get("专利号") or "",
        "申请时间": _safe_date(src.get("ad") or src.get("application_date") or src.get("申请日")) or "",
        "授权时间": _safe_date(src.get("pd") or src.get("grant_date") or src.get("授权公告日")) or "",
        "发明人": inventors or "",
        "当前法律状态": src.get("lsn1") or src.get("legal_status") or src.get("当前法律状态") or "",
        "最临近的一次缴纳年费截止日期": _safe_date(src.get("annu_due") or src.get("年费截止日期")) or "",
    }


def normalize_baiten_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and normalize list of items from Baiten API payload."""
    items = []
    # New style: documents list with nested field_values
    docs = payload.get("documents")
    if isinstance(docs, list):
        items = docs
    else:
        # Fallback common containers
        for key in ("data", "result", "rows", "list", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                items = val
                break
            if isinstance(val, dict) and isinstance(val.get("list"), list):
                items = val.get("list")
                break

    return [normalize_baiten_item(x) for x in items]


def build_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[REQUIRED_COLUMNS]
    return df
