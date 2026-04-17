import os
import sys

sys.path.append(os.path.dirname(__file__))
from connection import get_connection, test_connection


def run_setup():
    print("Testing HANA connection...")
    test_connection()

    init_sql_path = os.path.join(os.path.dirname(__file__), "init.sql")
    with open(init_sql_path, "r") as f:
        init_sql = f.read()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(init_sql)
        conn.commit()
        print("SAP_SYSTEM_LOGS — OK")
        print("SAP_LLM_LOGS    — OK")
        print("ANOMALY_RESULTS — OK")
        print("INCIDENTS       — OK")
        print("Schema setup complete.")
    except Exception as e:
        conn.rollback()
        print(f"Setup FAILED: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_setup()
