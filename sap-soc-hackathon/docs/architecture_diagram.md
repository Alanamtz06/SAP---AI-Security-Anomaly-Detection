# SAP SOC Platform — Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SAP BTP — Cloud Foundry                         │
│                  Org: d09533b9trial / Space: dev_hack               │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐                      │
│  │  soc-etl-pipeline│    │    ml-engine      │                      │
│  │  (Worker/daemon) │───▶│  (FastAPI :8080)  │                      │
│  │  Every 30 min    │    │  4 IF Models      │                      │
│  └──────────────────┘    └────────┬─────────┘                      │
│           │                       │                                  │
│           │ SAP API               │ ANOMALY_RESULTS                  │
│           ▼                       ▼                                  │
│  ┌──────────────────┐    ┌──────────────────┐                      │
│  │   SAP HANA Cloud │    │alerting-service  │                      │
│  │   (Hack_DB)      │◀───│  (Worker/daemon) │                      │
│  │                  │    │  Every 60 sec    │                      │
│  │ SAP_SYSTEM_LOGS  │    └────────┬─────────┘                      │
│  │ SAP_LLM_LOGS     │             │                                  │
│  │ ANOMALY_RESULTS  │             │ POST /alert                      │
│  │ INCIDENTS        │             ▼                                  │
│  └────────┬─────────┘    ┌──────────────────┐                      │
│           │               │  SAP API         │                      │
│           │               │  (External)      │                      │
│           ▼               └──────────────────┘                      │
│  ┌──────────────────┐                                               │
│  │   api-gateway    │                                               │
│  │  (FastAPI :8080) │                                               │
│  │  REST endpoints  │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│    ┌──────┴──────┐                                                  │
│    ▼             ▼                                                   │
│  ┌──────────┐ ┌──────────────┐                                     │
│  │soc-front │ │soc-streamlit │                                     │
│  │  (React) │ │  (Streamlit) │                                     │
│  └──────────┘ └──────────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘

External Data Source:
┌─────────────────────────────────────┐
│  SAP Log Ingestion API              │
│  https://sap-api-b2.679186.xyz      │
│  GET /logs/current (paginated)      │
│  POST /alert (webhook)              │
└─────────────────────────────────────┘
```

## Services

| Service | Type | URL | Purpose |
|---------|------|-----|---------|
| soc-etl-pipeline | Worker | No route | Ingests logs from SAP API every 30 min |
| ml-engine | Web | ml-engine.cfapps.us10-001.hana.ondemand.com | Scores logs with Isolation Forest |
| alerting-service | Worker | No route | Sends webhooks for anomalies every 60s |
| api-gateway | Web | api-gateway.cfapps.us10-001.hana.ondemand.com | REST API for frontend |
| soc-frontend | Web | soc-frontend.cfapps.us10-001.hana.ondemand.com | React dashboard |
| soc-streamlit | Web | soc-streamlit.cfapps.us10-001.hana.ondemand.com | Forensic analysis dashboard |

## ML Models

| Model | Source | Time Band | Contamination |
|-------|--------|-----------|---------------|
| IF_SYSTEM_PEAK | SAP_SYSTEM_LOGS | 08:00-18:00 | 2% |
| IF_SYSTEM_OFFPEAK | SAP_SYSTEM_LOGS | 18:00-08:00 | 4% |
| IF_LLM_PEAK | SAP_LLM_LOGS | 08:00-18:00 | 2% |
| IF_LLM_OFFPEAK | SAP_LLM_LOGS | 18:00-08:00 | 4% |

## Data Flow

1. **Ingest**: ETL Pipeline polls SAP API every 30 min → inserts into HANA
2. **Score**: ML Engine reads new logs → runs Isolation Forest → writes to ANOMALY_RESULTS
3. **Alert**: Alerting Service reads IS_ANOMALY=TRUE → creates INCIDENTS → POST /alert to SAP API
4. **Display**: API Gateway exposes data → React + Streamlit dashboards visualize
