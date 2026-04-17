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

POLL_INTERVAL = 300  # 5 minutes
RETRY_DELAY   = 60    # 1 minute on error


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    import sys
    
    test_connection()
    
    # Check if running in "daemon" mode (auto every 5 min)
    # or "manual" mode (run once and exit)
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        print("ETL Pipeline started in DAEMON mode. Polling every 5 minutes.")
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
    else:
        # Manual mode - run once and exit
        print("ETL Pipeline running in MANUAL mode (one-time execution).")
        try:
            print(f"\n[{now()}] Starting ingestion...")
            result = run_ingestion()
            print(
                f"[{now()}] Done — "
                f"total={result['total']} system={result['system_logs']} llm={result['llm_logs']}"
            )
            print("\nIngestion complete. Pipeline will exit.")
        except Exception as e:
            print(f"[{now()}] ERROR: {e}")
            sys.exit(1)
