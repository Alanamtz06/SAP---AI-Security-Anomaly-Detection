# HOW TO TEST LOCALLY:
# 1. Install dependencies:
#    pip install hdbcli requests
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
# 4. Run the full worker loop (daemon, aligned to :00 and :30 each hour):
#    python app.py --daemon

import time
from datetime import datetime, timezone

from connection import test_connection
from ingestion import run_ingestion

RETRY_DELAY = 60  # seconds to wait after a failed ingestion before retrying


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seconds_until_next_half_hour() -> float:
    """Return seconds until the next :00 or :30 mark (UTC), never negative."""
    t = datetime.now(timezone.utc)
    elapsed_in_half_hour = (t.minute % 30) * 60 + t.second + t.microsecond / 1_000_000
    wait = 1800 - elapsed_in_half_hour
    # If we are within 2 s of a mark, skip to the next one to avoid a double-fire
    return wait if wait > 2 else wait + 1800


if __name__ == "__main__":
    import sys

    test_connection()

    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        print("ETL Pipeline started in DAEMON mode — aligned to :00 and :30 each hour (UTC).")

        # Run once immediately so the first data arrives without waiting up to 30 min
        try:
            print(f"\n[{now()}] Starting initial ingestion...")
            result = run_ingestion()
            print(
                f"[{now()}] Done — "
                f"total={result['total']} system={result['system_logs']} llm={result['llm_logs']}"
            )
        except Exception as e:
            print(f"[{now()}] ERROR on startup ingestion: {e}")

        while True:
            wait = seconds_until_next_half_hour()
            next_mark = datetime.now(timezone.utc)
            print(f"[{now()}] Next ingestion in {wait:.0f}s")
            time.sleep(wait)

            try:
                print(f"\n[{now()}] Starting ingestion...")
                result = run_ingestion()
                print(
                    f"[{now()}] Done — "
                    f"total={result['total']} system={result['system_logs']} llm={result['llm_logs']}"
                )
            except Exception as e:
                print(f"[{now()}] ERROR: {e}")
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
    else:
        # Manual mode — run once and exit
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
