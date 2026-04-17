# Worker entry point — polls the SAP SOC API every 30 min and triggers ingestion
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../database'))
from connection import get_connection, execute_query, execute_insert, test_connection

test_connection()
