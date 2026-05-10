import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../database'))
from connection import execute_query

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()


def _serialize(row: dict) -> dict:
    for key, val in list(row.items()):
        if isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


@router.get("/logs")
def get_logs(
    source: str = Query(default="all"),
    limit: int = Query(default=100, ge=1),
):
    if source not in ("system", "llm", "all"):
        return JSONResponse(
            status_code=400,
            content={"error": "source must be 'system', 'llm', or 'all'"},
        )

    try:
        system_rows = []
        llm_rows = []

        if source in ("system", "all"):
            rows = execute_query(
                f"SELECT * FROM SAP_SYSTEM_LOGS ORDER BY TIMESTAMP DESC LIMIT {limit}"
            )
            for row in rows:
                row["source_type"] = "system"
                system_rows.append(_serialize(row))

        if source in ("llm", "all"):
            rows = execute_query(
                f"SELECT * FROM SAP_LLM_LOGS ORDER BY TIMESTAMP DESC LIMIT {limit}"
            )
            for row in rows:
                row["source_type"] = "llm"
                llm_rows.append(_serialize(row))

        if source == "all":
            combined = system_rows + llm_rows
            combined.sort(key=lambda r: r.get("TIMESTAMP", ""), reverse=True)
            return combined[:limit]

        return system_rows if source == "system" else llm_rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
