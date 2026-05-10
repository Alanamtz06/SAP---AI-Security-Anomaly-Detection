import os
from dotenv import load_dotenv
from src.db.connection import execute_query

load_dotenv()

print("=== Querying HANA ===\n")

try:
    # System logs count
    result = execute_query("SELECT COUNT(*) as cnt FROM SAP_SYSTEM_LOGS")
    print(f"✓ System logs: {result[0]['CNT']:,} records")
    
    # LLM logs count
    result = execute_query("SELECT COUNT(*) as cnt FROM SAP_LLM_LOGS")
    print(f"✓ LLM logs: {result[0]['CNT']:,} records")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()