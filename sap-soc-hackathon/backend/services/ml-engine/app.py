from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import pandas as pd

from connection import execute_query
from scoring_engine import ScoringEngine

load_dotenv()

app = FastAPI()
engine = ScoringEngine()


@app.get('/health')
def health():
    return {"status": "ok", "models": engine.training_status()}


@app.get('/ready')
def ready():
    if engine.is_ready():
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": engine.training_status()})


@app.post('/train')
def train():
    """Manually trigger model re-training."""
    if engine._training:
        return JSONResponse(status_code=409, content={"status": "already_training"})
    import threading
    engine._ready = False
    engine._training = True
    t = threading.Thread(target=engine._train_and_load, daemon=True)
    t.start()
    return {"status": "training_started"}


@app.post('/score')
def score():
    if not engine.is_ready():
        return JSONResponse(
            status_code=503,
            content={"status": engine.training_status(),
                     "message": "Models are being trained, retry in a few minutes"}
        )
    try:
        query = """
        SELECT L.ID, L.TIMESTAMP, L.LOG_TYPE, L.HTTP_STATUS_CODE, L.CLIENT_IP, L.SERVICE_ID
        FROM SAP_SYSTEM_LOGS L
        WHERE NOT EXISTS (
            SELECT 1 FROM ANOMALY_RESULTS AR
            WHERE AR.SOURCE_TABLE = 'SYSTEM' AND AR.SOURCE_ID = L.ID
        )
        LIMIT 1000
        """
        system_logs = execute_query(query)
        if not system_logs:
            return {"status": "no_new_logs"}

        df_sys = pd.DataFrame(system_logs)
        results = engine.score_batch('SYSTEM', df_sys)
        engine.insert_results(results)
        anomalies = results[results['IS_ANOMALY'] == True].shape[0]

        return {
            "status": "success",
            "records_processed": len(results),
            "anomalies_detected": anomalies
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post('/score-llm')
def score_llm():
    if not engine.is_ready():
        return JSONResponse(
            status_code=503,
            content={"status": engine.training_status(),
                     "message": "Models are being trained, retry in a few minutes"}
        )
    try:
        query = """
        SELECT L.ID, L.TIMESTAMP, L.LOG_TYPE, L.LLM_MODEL_ID, L.LLM_STATUS,
               L.LLM_COST_USD, L.LLM_RESPONSE_TIME_MS
        FROM SAP_LLM_LOGS L
        WHERE NOT EXISTS (
            SELECT 1 FROM ANOMALY_RESULTS AR
            WHERE AR.SOURCE_TABLE = 'LLM' AND AR.SOURCE_ID = L.ID
        )
        LIMIT 1000
        """
        llm_logs = execute_query(query)
        if not llm_logs:
            return {"status": "no_new_logs"}

        df_llm = pd.DataFrame(llm_logs)
        results = engine.score_batch('LLM', df_llm)
        engine.insert_results(results)
        anomalies = results[results['IS_ANOMALY'] == True].shape[0]

        return {
            "status": "success",
            "records_processed": len(results),
            "anomalies_detected": anomalies
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8001)
