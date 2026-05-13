from connection import execute_query

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional

router = APIRouter()


def _serialize(row: dict) -> dict:
    for key, val in list(row.items()):
        if isinstance(val, datetime):
            row[key] = val.isoformat()
        if key in ("ALERT_SENT", "RESOLVED"):
            row[key] = bool(val)
    return row


@router.get("/incidents")
def get_incidents(
    limit: int = Query(default=50, ge=1),
    resolved: Optional[bool] = Query(default=None),
):
    try:
        where = ""
        if resolved is not None:
            where = f" WHERE I.RESOLVED = {'TRUE' if resolved else 'FALSE'}"

        sql = f"""
            SELECT I.ID, I.ANOMALY_ID, I.SEVERITY, I.ATTACK_TYPE, I.ALERT_SENT,
                   I.WEBHOOK_STATUS, I.RESOLVED, I.CREATED_AT,
                   AR.ANOMALY_SCORE, AR.SOURCE_TABLE
            FROM INCIDENTS I
            JOIN ANOMALY_RESULTS AR ON I.ANOMALY_ID = AR.ID
            {where}
            ORDER BY I.CREATED_AT DESC
            LIMIT {limit}
        """
        rows = execute_query(sql)
        return [_serialize(row) for row in rows]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
