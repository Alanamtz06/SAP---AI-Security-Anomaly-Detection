import os
import requests
import logging

logger = logging.getLogger(__name__)

API_BASE = "https://sap-api-b2.679186.xyz"


def send_alert_to_sap(anomaly_id: int, anomaly_score: float, detected_at: str,
                      source_table: str, source_id: int, anomaly_type: str) -> bool:
    api_key = os.environ.get('SAP_API_KEY')
    if not api_key:
        logger.error("SAP_API_KEY not set — skipping alert")
        return False

    try:
        if source_table == 'SYSTEM':
            what = f"Anomalous system activity detected (type: {anomaly_type})"
        else:
            what = f"Anomalous LLM interaction detected (type: {anomaly_type})"

        confidence = int(anomaly_score * 100)
        why = f"ML model flagged with {confidence}% anomaly confidence (source_id: {source_id})"
        message = f"WHAT: {what}. WHEN: {detected_at}. WHY: {why}."

        if len(message) > 300:
            message = message[:297] + "..."

        logger.info(f"Alert message ({len(message)} chars): {message}")

        response = requests.post(
            f"{API_BASE}/alert",
            json={"message": message},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code == 201:
            logger.info(f"Alert sent for anomaly {anomaly_id}: {response.json()}")
            return True
        else:
            logger.warning(f"Alert failed for anomaly {anomaly_id}: HTTP {response.status_code} — {response.text}")
            return False

    except Exception as e:
        logger.error(f"Exception sending alert for anomaly {anomaly_id}: {e}")
        return False
