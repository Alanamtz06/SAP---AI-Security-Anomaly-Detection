import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_BASE = "https://sap-api-b2.679186.xyz"
API_KEY = os.environ.get('SAP_API_KEY')


def send_alert_to_sap(anomaly_id: int, anomaly_score: float, detected_at: str,
                      source_table: str, source_id: int, anomaly_type: str) -> bool:
    """
    Send alert to POST /alert on the SAP API.

    Builds a WHAT/WHEN/WHY message in English (max 300 chars).
    Requires a Bearer token via the SAP_API_KEY environment variable.

    Returns True on success (HTTP 201), False otherwise.
    """
    try:
        if source_table == 'SYSTEM':
            what = f"Anomalous system activity detected (type: {anomaly_type})"
        else:
            what = f"Anomalous LLM interaction detected (type: {anomaly_type})"

        when = detected_at

        confidence = int(anomaly_score * 100)
        why = f"ML model flagged with {confidence}% anomaly confidence (source_id: {source_id})"

        message = f"WHAT: {what}. WHEN: {when}. WHY: {why}."

        if len(message) > 300:
            message = message[:297] + "..."

        logger.info(f"Alert message ({len(message)} chars): {message}")

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{API_BASE}/alert",
            json={"message": message},
            headers=headers,
            timeout=10
        )

        if response.status_code == 201:
            logger.info(f"Alert sent successfully for anomaly {anomaly_id}: {response.json()}")
            return True
        else:
            logger.warning(f"Alert failed for anomaly {anomaly_id}: HTTP {response.status_code} — {response.text}")
            return False

    except Exception as e:
        logger.error(f"Exception sending alert for anomaly {anomaly_id}: {e}")
        return False
