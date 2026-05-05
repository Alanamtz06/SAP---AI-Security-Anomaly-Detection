import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_BASE = "https://sap-api-b2.679186.xyz"
API_KEY = os.environ.get('SAP_API_KEY')

def send_alert_to_sap(anomaly_id: int, anomaly_score: float, detected_at: str,
                      source_table: str, source_id: int, anomaly_type: str) -> bool:
    """
    Envía alerta a POST /alert del API de SAP.

    Construye mensaje WHAT/WHEN/WHY en inglés (max 300 chars).
    Requiere Bearer token en Authorization header.

    Returns: True si exitoso (201), False si falló
    """

    try:
        # 1. Determinar WHAT (qué pasó)
        if source_table == 'SYSTEM':
            what = f"Anomalous system activity detected (type: {anomaly_type})"
        else:  # LLM
            what = f"Anomalous LLM interaction detected (type: {anomaly_type})"

        # 2. WHEN (cuándo pasó) — timestamp ISO
        when = detected_at

        # 3. WHY (por qué fue detectado) — score de confianza
        confidence = int(anomaly_score * 100)
        why = f"ML model flagged with {confidence}% anomaly confidence (source_id: {source_id})"

        # 4. Construir mensaje (max 300 chars)
        message = f"WHAT: {what}. WHEN: {when}. WHY: {why}."

        # Truncar si excede 300 caracteres
        if len(message) > 300:
            message = message[:297] + "..."

        logger.info(f"Alert message ({len(message)} chars): {message}")

        # 5. Enviar POST /alert
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "message": message
        }

        response = requests.post(
            f"{API_BASE}/alert",
            json=payload,
            headers=headers,
            timeout=10
        )

        # 6. Verificar respuesta
        if response.status_code == 201:
            logger.info(f"✓ Alert sent successfully for anomaly {anomaly_id}")
            logger.info(f"  Response: {response.json()}")
            return True
        else:
            logger.warning(f"✗ Alert failed for anomaly {anomaly_id}: {response.status_code}")
            logger.warning(f"  Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Exception sending alert for anomaly {anomaly_id}: {e}")
        return False
