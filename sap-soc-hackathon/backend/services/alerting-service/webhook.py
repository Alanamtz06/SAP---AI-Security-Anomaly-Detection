import os
import time
import logging
import requests
from typing import Optional

_API_BASE = os.environ.get("SAP_API_URL", "https://sap-api-b2.679186.xyz")
_API_KEY  = os.environ.get("SAP_API_KEY", "")

_MAX_RETRIES = 3
_TIMEOUT_SEC = 5
_MAX_MSG_LEN = 300

log = logging.getLogger(__name__)


def _try_request(
    url: str, payload: dict, headers: dict, attempt: int
) -> Optional[str]:
    """One HTTP attempt. Returns 'SUCCESS'/'FAILED' if done, None to retry."""
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT_SEC)
        if resp.status_code == 200:
            log.info(f"[webhook] alert sent OK (attempt {attempt + 1})")
            return "SUCCESS"
        if 400 <= resp.status_code < 500:
            log.warning(f"[webhook] HTTP {resp.status_code} (4xx, no retry): {resp.text[:120]}")
            return "FAILED"
        log.warning(
            f"[webhook] attempt {attempt + 1}/{_MAX_RETRIES} — HTTP {resp.status_code}: {resp.text[:120]}"
        )
    except requests.Timeout:
        log.warning(f"[webhook] attempt {attempt + 1}/{_MAX_RETRIES} timed out after {_TIMEOUT_SEC}s")
    except requests.RequestException as exc:
        log.warning(f"[webhook] attempt {attempt + 1}/{_MAX_RETRIES} network error: {exc}")
    return None  # 5xx or network error — caller will retry


def send_alert(
    message: str,
    severity: str,
    anomaly_id: Optional[int] = None,
    incident_id: Optional[int] = None,
    attack_type: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """POST alert to SAP SOC API with exponential-backoff retry.

    Returns 'SUCCESS' or 'FAILED'.
    """
    url = f"{_API_BASE}/alert"
    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: dict = {"message": message[:_MAX_MSG_LEN], "severity": severity}
    if anomaly_id is not None:
        payload["anomaly_id"] = anomaly_id
    if incident_id is not None:
        payload["incident_id"] = incident_id
    if attack_type is not None:
        payload["attack_type"] = attack_type
    if timestamp is not None:
        payload["timestamp"] = timestamp

    for attempt in range(_MAX_RETRIES):
        result = _try_request(url, payload, headers, attempt)
        if result is not None:
            return result
        if attempt < _MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # 1s, 2s

    log.error(f"[webhook] all {_MAX_RETRIES} attempts failed")
    return "FAILED"
