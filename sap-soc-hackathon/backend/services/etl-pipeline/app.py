import os
import sys
import time
import logging
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

from connection import test_connection, execute_insert
from ingestion import run_ingestion

load_dotenv()

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL_SECONDS', 120))
ML_ENGINE_URL = os.environ.get('ML_ENGINE_URL', 'http://localhost:8001')

def record_cycle(cycle_start, cycle_end, records_processed, anomalies_detected, status='SUCCESS', error=None):
    """Registra ciclo en PIPELINE_HEALTH"""
    try:
        sql = """
        INSERT INTO PIPELINE_HEALTH
        (CYCLE_START, CYCLE_END, RECORDS_PROCESSED, ANOMALIES_DETECTED, STATUS, ERROR_MESSAGE, POLL_INTERVAL_SECONDS)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        execute_insert(sql, [(cycle_start, cycle_end, records_processed, anomalies_detected, status, error, POLL_INTERVAL)])
        logger.info(f"✓ Cycle recorded in PIPELINE_HEALTH")
    except Exception as e:
        logger.error(f"Could not record cycle: {e}")

def call_ml_engine():
    """Llama a ml-engine para procesar logs nuevos"""
    try:
        logger.info("Calling ml-engine...")
        response = requests.post(
            f"{ML_ENGINE_URL}/score",
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ ML Engine: {result.get('records_processed')} processed, {result.get('anomalies_detected')} anomalies")
            return result.get('anomalies_detected', 0)
        else:
            logger.warning(f"⚠ ML Engine error: {response.status_code}")
            return 0
    except Exception as e:
        logger.warning(f"⚠ ML Engine call failed: {e}")
        return 0

def polling_loop():
    """Loop que ejecuta ETL cada POLL_INTERVAL segundos"""
    logger.info(f"ETL Pipeline started - polling every {POLL_INTERVAL} seconds")
    logger.info(f"ML Engine URL: {ML_ENGINE_URL}")

    while True:
        cycle_start = datetime.now(timezone.utc)
        try:
            logger.info("="*60)
            logger.info("Starting ETL Cycle")
            logger.info("="*60)

            # 1. Ejecutar ingestion
            result = run_ingestion()
            total_records = result.get('total', 0)
            system_logs = result.get('system_logs', 0)
            llm_logs = result.get('llm_logs', 0)

            logger.info(f"✓ Ingestion complete: {system_logs} system, {llm_logs} LLM logs (total: {total_records})")

            # 2. Llamar ml-engine
            anomalies_detected = call_ml_engine()

            # 3. Registrar ciclo
            cycle_end = datetime.now(timezone.utc)
            record_cycle(cycle_start, cycle_end, total_records, anomalies_detected, status='SUCCESS')

            logger.info(f"✓ Cycle complete. Next cycle in {POLL_INTERVAL}s\n")

        except Exception as e:
            cycle_end = datetime.now(timezone.utc)
            logger.error(f"✗ Cycle failed: {e}")
            record_cycle(cycle_start, cycle_end, 0, 0, status='FAILED', error=str(e))
            logger.info(f"Retrying in {POLL_INTERVAL}s\n")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    test_connection()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        logger.info("Starting in DAEMON mode")
        polling_loop()
    else:
        logger.info("Running in MANUAL mode (single execution)")
        try:
            result = run_ingestion()
            anomalies = call_ml_engine()
            logger.info(f"Done - {result['total']} records, {anomalies} anomalies")
        except Exception as e:
            logger.error(f"ERROR: {e}")
            sys.exit(1)
