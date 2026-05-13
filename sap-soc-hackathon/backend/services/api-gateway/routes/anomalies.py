from connection import execute_query

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()


def _serialize(row: dict) -> dict:
    for key, val in list(row.items()):
        if isinstance(val, datetime):
            row[key] = val.isoformat()
        if key == "IS_ANOMALY":
            row[key] = bool(val)
    return row


@router.get("/anomalies")
def get_anomalies(
    limit: int = Query(default=50, ge=1, le=200),
    only_anomalies: bool = Query(default=True),
):
    try:
        where = " WHERE IS_ANOMALY = TRUE" if only_anomalies else ""
        sql = f"SELECT * FROM ANOMALY_RESULTS{where} ORDER BY DETECTED_AT DESC LIMIT {limit}"
        rows = execute_query(sql)
        return [_serialize(row) for row in rows]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
