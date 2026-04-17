# HOW TO TEST LOCALLY:
# 1. Install dependencies:
#    pip install hdbcli requests pandas
#
# 2. Run a single ingestion manually:
#    python -c "from ingestion import run_ingestion; run_ingestion()"
#
# 3. Verify data arrived in HANA:
#    python -c "
#    import sys, os; sys.path.append('../../database')
#    from connection import execute_query
#    r = execute_query('SELECT COUNT(*) AS N FROM SAP_SYSTEM_LOGS')
#    print('System logs:', r)
#    r = execute_query('SELECT COUNT(*) AS N FROM SAP_LLM_LOGS')
#    print('LLM logs:', r)
#    "
#
# 4. Run the full worker loop:
#    python app.py

import time
from datetime import datetime, timezone

from connection import test_connection
from ingestion import run_ingestion

POLL_INTERVAL = 1800  # 30 minutes
RETRY_DELAY   = 60    # 1 minute on error


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


test_connection()
print("ETL Pipeline started. Polling every 30 minutes.")

while True:
    try:
        print(f"\n[{now()}] Starting ingestion...")
        result = run_ingestion()
        print(
            f"[{now()}] Done — "
            f"total={result['total']} system={result['system_logs']} llm={result['llm_logs']}"
        )
        time.sleep(POLL_INTERVAL)
    except Exception as e:
        print(f"[{now()}] ERROR: {e}")
        print(f"Retrying in {RETRY_DELAY} seconds...")
        time.sleep(RETRY_DELAY)
