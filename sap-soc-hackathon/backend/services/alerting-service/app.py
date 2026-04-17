# Worker — polls ANOMALY_RESULTS in HANA and fires webhooks for confirmed threats
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../database'))
from connection import get_connection, execute_query, execute_insert, test_connection

test_connection()
