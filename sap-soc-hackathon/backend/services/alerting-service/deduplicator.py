from typing import Any, Optional

DEDUP_WINDOW_SEC = 1800  # 30 minutes


def should_create_incident(
    conn: Any,
    anomaly_type: str,
    source_table: str,
    source_id: int,
) -> tuple[bool, Optional[int]]:
    """Check whether a recent unresolved incident already covers this threat fingerprint.

    Returns (True, None)   → no duplicate, create a new incident
    Returns (False, int)   → duplicate found, increment that incident's occurrence count
    """
    cur = conn.cursor()

    if source_table == "SYSTEM":
        cur.execute(
            """
            SELECT i.ID
            FROM   INCIDENTS i
            JOIN   ANOMALY_RESULTS ar ON i.ANOMALY_ID = ar.ID
            JOIN   SAP_SYSTEM_LOGS sl ON sl.ID = ar.SOURCE_ID
            WHERE  ar.ANOMALY_TYPE = ?
              AND  ar.SOURCE_TABLE = 'SYSTEM'
              AND  sl.CLIENT_IP    = (SELECT CLIENT_IP FROM SAP_SYSTEM_LOGS WHERE ID = ?)
              AND  i.RESOLVED      = FALSE
              AND  i.WEBHOOK_STATUS <> 'DEDUP'
              AND  i.CREATED_AT   > ADD_SECONDS(CURRENT_TIMESTAMP, ?)
            ORDER BY i.CREATED_AT DESC
            LIMIT 1
            """,
            (anomaly_type, source_id, -DEDUP_WINDOW_SEC),
        )
    elif source_table == "LLM":
        cur.execute(
            """
            SELECT i.ID
            FROM   INCIDENTS i
            JOIN   ANOMALY_RESULTS ar ON i.ANOMALY_ID = ar.ID
            JOIN   SAP_LLM_LOGS   ll ON ll.ID = ar.SOURCE_ID
            WHERE  ar.ANOMALY_TYPE  = ?
              AND  ar.SOURCE_TABLE  = 'LLM'
              AND  ll.LLM_MODEL_ID  = (SELECT LLM_MODEL_ID FROM SAP_LLM_LOGS WHERE ID = ?)
              AND  i.RESOLVED       = FALSE
              AND  i.WEBHOOK_STATUS <> 'DEDUP'
              AND  i.CREATED_AT    > ADD_SECONDS(CURRENT_TIMESTAMP, ?)
            ORDER BY i.CREATED_AT DESC
            LIMIT 1
            """,
            (anomaly_type, source_id, -DEDUP_WINDOW_SEC),
        )
    else:
        cur.execute(
            """
            SELECT i.ID
            FROM   INCIDENTS i
            JOIN   ANOMALY_RESULTS ar ON i.ANOMALY_ID = ar.ID
            WHERE  ar.ANOMALY_TYPE = ?
              AND  ar.SOURCE_TABLE = ?
              AND  i.RESOLVED      = FALSE
              AND  i.WEBHOOK_STATUS <> 'DEDUP'
              AND  i.CREATED_AT   > ADD_SECONDS(CURRENT_TIMESTAMP, ?)
            ORDER BY i.CREATED_AT DESC
            LIMIT 1
            """,
            (anomaly_type, source_table, -DEDUP_WINDOW_SEC),
        )

    row = cur.fetchone()
    cur.close()

    if row:
        return False, int(row[0])
    return True, None
