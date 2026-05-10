import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../database'))
from connection import get_connection, execute_query, execute_insert, test_connection

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes.anomalies import router as anomalies_router
from routes.incidents import router as incidents_router
from routes.stats import router as stats_router
from routes.logs import router as logs_router

test_connection()

app = FastAPI(title="SAP Security Anomaly Detection — API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anomalies_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(logs_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
