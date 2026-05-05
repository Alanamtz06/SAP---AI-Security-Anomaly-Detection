import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('../../src'))
sys.path.insert(0, os.path.abspath('../../services/etl-pipeline'))

from db.connection import execute_query, get_connection, test_connection
from webhook import send_alert_to_sap

load_dotenv()

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_severity(anomaly_score: float) -> str:
    """Mapea anomaly_score a severidad"""
    if anomaly_score >= 0.8:
        return 'CRITICAL'
    elif anomaly_score >= 0.6:
        return 'HIGH'
    elif anomaly_score >= 0.4:
        return 'MEDIUM'
    else:
        return 'LOW'

def get_new_anomalies():
    """Obtiene anomalías sin incident creado (IS_ANOMALY=TRUE)"""
    query = """
    SELECT AR.ID, AR.SOURCE_TABLE, AR.SOURCE_ID, AR.ANOMALY_SCORE,
           AR.ANOMALY_TYPE, AR.DETECTED_AT
    FROM ANOMALY_RESULTS AR
    WHERE AR.IS_ANOMALY = TRUE
    AND NOT EXISTS (
        SELECT 1 FROM INCIDENTS I WHERE I.ANOMALY_ID = AR.ID
    )
    LIMIT 100
    """
    try:
        return execute_query(query)
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        return []

def create_incident(anomaly_id: int, severity: str, anomaly_type: str = None) -> int:
    """Crea incident en INCIDENTS table. Retorna incident_id."""
    sql = """
    INSERT INTO INCIDENTS
    (ANOMALY_ID, SEVERITY, ATTACK_TYPE, WEBHOOK_STATUS, ALERT_SENT)
    VALUES (?, ?, ?, 'PENDING', FALSE)
    """
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (anomaly_id, severity, anomaly_type or 'Unknown'))
            conn.commit()
        finally:
            conn.close()

        # Obtener el ID creado
        result = execute_query(
            f"SELECT ID FROM INCIDENTS WHERE ANOMALY_ID = {anomaly_id} ORDER BY CREATED_AT DESC LIMIT 1"
        )
        if result:
            incident_id = result[0]['ID']
            logger.info(f"✓ Created incident {incident_id} for anomaly {anomaly_id}")
            return incident_id
        return None
    except Exception as e:
        logger.error(f"Error creating incident for anomaly {anomaly_id}: {e}")
        return None

def update_incident_webhook_status(incident_id: int, status: str):
    """Actualiza WEBHOOK_STATUS e ALERT_SENT en INCIDENTS"""
    sql = """
    UPDATE INCIDENTS
    SET WEBHOOK_STATUS = ?, ALERT_SENT = ?
    WHERE ID = ?
    """
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (status, status == 'SUCCESS', incident_id))
            conn.commit()
        finally:
            conn.close()
        logger.info(f"✓ Updated incident {incident_id} webhook_status to {status}")
    except Exception as e:
        logger.error(f"Error updating incident {incident_id}: {e}")

def process_alerts():
    """Procesa anomalías nuevas: crea incidents y envía webhooks"""
    logger.info("="*60)
    logger.info("Starting alert processing cycle")
    logger.info("="*60)

    # 1. Obtener anomalías nuevas
    anomalies = get_new_anomalies()

    if not anomalies:
        logger.info("No new anomalies to alert")
        return {"status": "no_new_anomalies", "count": 0}

    logger.info(f"Found {len(anomalies)} new anomalies")

    alerts_sent = 0
    alerts_failed = 0

    # 2. Procesar cada anomalía
    for anomaly in anomalies:
        try:
            anomaly_id = anomaly['ID']
            severity = get_severity(anomaly['ANOMALY_SCORE'])

            logger.info(f"\nProcessing anomaly {anomaly_id} (score: {anomaly['ANOMALY_SCORE']:.3f}, severity: {severity})")

            # 2a. Crear incident
            incident_id = create_incident(anomaly_id, severity, anomaly['ANOMALY_TYPE'])
            if not incident_id:
                logger.warning(f"Failed to create incident for anomaly {anomaly_id}")
                continue

            # 2b. Enviar webhook
            webhook_success = send_alert_to_sap(
                anomaly_id=anomaly_id,
                anomaly_score=anomaly['ANOMALY_SCORE'],
                detected_at=anomaly['DETECTED_AT'].isoformat() if hasattr(anomaly['DETECTED_AT'], 'isoformat') else str(anomaly['DETECTED_AT']),
                source_table=anomaly['SOURCE_TABLE'],
                source_id=anomaly['SOURCE_ID'],
                anomaly_type=anomaly['ANOMALY_TYPE'] or 'Unknown'
            )

            # 2c. Actualizar webhook_status
            webhook_status = 'SUCCESS' if webhook_success else 'FAILED'
            update_incident_webhook_status(incident_id, webhook_status)

            if webhook_success:
                alerts_sent += 1
            else:
                alerts_failed += 1

        except Exception as e:
            logger.error(f"Error processing anomaly {anomaly['ID']}: {e}")
            alerts_failed += 1

    logger.info("\n" + "="*60)
    logger.info(f"Alert cycle complete: {alerts_sent} sent, {alerts_failed} failed")
    logger.info("="*60 + "\n")

    return {
        "status": "success",
        "anomalies_processed": len(anomalies),
        "alerts_sent": alerts_sent,
        "alerts_failed": alerts_failed
    }

if __name__ == '__main__':
    logger.info("Alerting Service initialized")
    test_connection()
    result = process_alerts()
    logger.info(f"Result: {result}")
