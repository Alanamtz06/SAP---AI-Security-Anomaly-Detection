from connection import execute_query

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/stats")
def get_stats():
    try:
        sys_count = execute_query("SELECT COUNT(*) AS CNT FROM SAP_SYSTEM_LOGS")[0]["CNT"] or 0
        llm_count = execute_query("SELECT COUNT(*) AS CNT FROM SAP_LLM_LOGS")[0]["CNT"] or 0

        total_anomalies = execute_query(
            "SELECT COUNT(*) AS CNT FROM ANOMALY_RESULTS WHERE IS_ANOMALY = TRUE"
        )[0]["CNT"] or 0

        open_incidents = execute_query(
            "SELECT COUNT(*) AS CNT FROM INCIDENTS WHERE RESOLVED = FALSE"
        )[0]["CNT"] or 0

        alerts_sent = execute_query(
            "SELECT COUNT(*) AS CNT FROM INCIDENTS WHERE ALERT_SENT = TRUE"
        )[0]["CNT"] or 0

        avg_row = execute_query(
            "SELECT AVG(ANOMALY_SCORE) AS AVG_SCORE FROM ANOMALY_RESULTS WHERE IS_ANOMALY = TRUE"
        )[0]["AVG_SCORE"]
        avg_anomaly_score = round(float(avg_row), 4) if avg_row is not None else None

        mttd_row = execute_query("""
            SELECT ROUND(AVG(SECONDS_BETWEEN(SL.TIMESTAMP, AR.DETECTED_AT)), 1) AS MTTD
            FROM ANOMALY_RESULTS AR
            JOIN SAP_SYSTEM_LOGS SL ON AR.SOURCE_ID = SL.ID
            WHERE AR.SOURCE_TABLE = 'SYSTEM'
        """)[0]["MTTD"]
        mttd_seconds = float(mttd_row) if mttd_row is not None else None

        return {
            "total_logs": int(sys_count) + int(llm_count),
            "total_anomalies": int(total_anomalies),
            "open_incidents": int(open_incidents),
            "alerts_sent": int(alerts_sent),
            "avg_anomaly_score": avg_anomaly_score,
            "mttd_seconds": mttd_seconds,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
