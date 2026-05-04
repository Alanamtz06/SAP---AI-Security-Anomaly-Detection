import os
import sys
from dotenv import load_dotenv

print("Step 1: Loading .env...", flush=True)
load_dotenv()

print("Step 2: Checking env vars...", flush=True)
print(f"  HANA_PASS exists: {bool(os.environ.get('HANA_PASS'))}", flush=True)
print(f"  SAP_API_KEY exists: {bool(os.environ.get('SAP_API_KEY'))}", flush=True)

print("Step 3: Importing connection...", flush=True)
try:
    from src.db.connection import test_connection, execute_query
    print("  Import OK", flush=True)
except Exception as e:
    print(f"  Import FAILED: {e}", flush=True)
    sys.exit(1)

print("Step 4: Testing connection...", flush=True)
try:
    if test_connection():
        print("Step 5: Querying data...", flush=True)
        result_sys = execute_query("SELECT COUNT(*) as cnt FROM SAP_SYSTEM_LOGS")
        print(f"  Result: {result_sys}", flush=True)
    else:
        print("  Connection test failed", flush=True)
except Exception as e:
    print(f"  Query FAILED: {e}", flush=True)
    import traceback
    traceback.print_exc()