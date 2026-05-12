import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from connection import execute_insert

BASE_URL = "https://sap-api-b2.679186.xyz"
API_KEY = os.environ.get("SAP_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

LLM_TYPES = {"LLM_REQUEST", "LLM_ERROR", "LLM_TIMEOUT"}

INSERT_SYSTEM = """
INSERT INTO SAP_SYSTEM_LOGS
    (TIMESTAMP, LOG_TYPE, HTTP_STATUS_CODE, CLIENT_IP, SERVICE_ID, WINDOW_START)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_LLM = """
INSERT INTO SAP_LLM_LOGS
    (TIMESTAMP, LOG_TYPE, LLM_MODEL_ID, LLM_STATUS, LLM_COST_USD, LLM_RESPONSE_TIME_MS, WINDOW_START)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def _parse_ts(ts_str):
    if not ts_str:
        return None
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)


def _val(v):
    """Convert empty string or None to None."""
    if v is None or v == "":
        return None
    return v


def _int_val(v):
    """Convert string like '200.0' to int, or None."""
    v = _val(v)
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _float_val(v):
    v = _val(v)
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _check_health():
    resp = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"API health check failed: {data}")


def _get_info():
    resp = requests.get(f"{BASE_URL}/info", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fetch_page(page: int):
    resp = requests.get(
        f"{BASE_URL}/logs/current",
        headers=HEADERS,
        params={"page": page},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def run_ingestion() -> dict:
    _check_health()

    info = _get_info()
    page_count = info["total_pages"]
    window_start = _parse_ts(info.get("window_start"))

    all_logs = []
    for page in range(1, page_count + 1):
        logs = _fetch_page(page)
        all_logs.extend(logs)
        print(f"  Fetched page {page}/{page_count} — {len(logs)} records")

    system_rows = []
    llm_rows = []

    for log in all_logs:
        log_type = _val(log.get("sap_function_log_type")) or "INFO"
        ts = _parse_ts(log.get("@timestamp"))

        if log_type in LLM_TYPES:
            llm_rows.append((
                ts,
                log_type,
                _val(log.get("llm_model_id")),
                _val(log.get("llm_status")),
                _float_val(log.get("llm_cost_usd")),
                _int_val(log.get("llm_response_time_ms")),
                window_start,
            ))
        else:
            system_rows.append((
                ts,
                log_type,
                _int_val(log.get("http_status_code")),
                _val(log.get("client_ip")),
                _val(log.get("service_id")),
                window_start,
            ))

    if system_rows:
        execute_insert(INSERT_SYSTEM, system_rows)
    if llm_rows:
        execute_insert(INSERT_LLM, llm_rows)

    total = len(all_logs)
    print(f"Ingestion complete — total: {total}, system: {len(system_rows)}, LLM: {len(llm_rows)}")

    return {
        "total": total,
        "system_logs": len(system_rows),
        "llm_logs": len(llm_rows),
        "window_start": info.get("window_start"),
    }
