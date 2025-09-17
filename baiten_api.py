import hashlib
import requests
from typing import Dict, Any, Optional, Tuple


def _md5_hex(s: str, enc: str = "utf-8", upper: bool = False) -> str:
    h = hashlib.md5(s.encode(enc)).hexdigest()
    return h.upper() if upper else h


def _looks_success(resp: requests.Response) -> Tuple[bool, Dict[str, Any]]:
    """Check success by common convention: HTTP 200 and code in {200, 0}."""
    if resp.status_code != 200:
        return False, {"_raw_text": resp.text}
    try:
        js = resp.json()
    except Exception:
        return False, {"_raw_text": resp.text}
    code = str(js.get("code", "200"))
    return (code in ("200", "0")), js


def search_baiten_post(
    app_key: str,
    app_secret: str,
    query: str,
    *,
    url: str = "http://open.baiten.cn/router/openService/search",
    page_index: int = 1,
    page_size: int = 10,
    sort_field: str = "ad_sort",
    sort: str = "desc",
    level: str = "TWO",
    source: int = 63,
    timeout: int = 15,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    POST call to Baiten search API.

    Signing rule per provided snippet: md5("2025" + len(query) + app_secret) with variations
    on encoding and hex case attempted automatically.

    Returns
    -------
    dict
        If success: {
            ok: True,
            which: {encoding, upper},
            client_sign, request_data, response, http_status, raw_str
        }
        Else: {ok: False, attempts, last_response, http_status, raw_str, hint}
    """
    raw_str = "2025" + str(len(query)) + app_secret
    tries = [
        ("utf-8", False),
        ("utf-8", True),
        ("gbk", False),
        ("gbk", True),
    ]

    # Clamp parameters to API constraints
    page_size = max(1, min(int(page_size or 10), 10))
    page_index = max(1, int(page_index or 1))

    base_data = {
        "app_key": app_key,
        "query": query,
        "sort_field": sort_field,
        "level": level,
        "page_index": page_index,
        "sort": sort,
        "source": source,
        "page_size": page_size,
    }
    if extra_params:
        base_data.update(extra_params)

    attempts = []
    last_resp = None
    last_payload: Optional[Dict[str, Any]] = None

    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

    for enc, upper in tries:
        client_sign = _md5_hex(raw_str, enc=enc, upper=upper)
        data = dict(base_data)
        data["client_sign"] = client_sign

        try:
            resp = requests.post(url, data=data, headers=headers, timeout=timeout)
        except Exception as e:
            attempts.append(
                {
                    "encoding": enc,
                    "upper": upper,
                    "client_sign": client_sign,
                    "network_error": str(e),
                }
            )
            continue

        last_resp = resp
        ok, payload = _looks_success(resp)
        last_payload = payload

        attempts.append(
            {
                "encoding": enc,
                "upper": upper,
                "client_sign": client_sign,
                "http_status": resp.status_code,
                "snippet": str(payload)[:200],
            }
        )

        if ok:
            return {
                "ok": True,
                "which": {"encoding": enc, "upper": upper},
                "client_sign": client_sign,
                "request_data": data,
                "response": payload,
                "http_status": resp.status_code,
                "raw_str": raw_str,
            }

    return {
        "ok": False,
        "attempts": attempts,
        "last_response": last_payload,
        "http_status": getattr(last_resp, "status_code", None),
        "raw_str": raw_str,
        "hint": (
            "Check if other params need to be included in signature and sorted by ASCII, "
            "and confirm final case/encoding requirements."
        ),
    }
