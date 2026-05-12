# SAP SOC Platform — Technical Report
**Team:** CTRL_C_CTRL_V | **Hackathon:** SAP x Tec de Monterrey 2026

---

## 1. Executive Summary

We built a real-time AI Security Operations Center (SOC) platform that automatically:
- Ingests 4.2M+ security logs from SAP systems
- Detects anomalies using 4 Isolation Forest ML models
- Sends automated alerts via webhook within 60 seconds of detection
- Visualizes threats in real-time dashboards

**Key Metrics:**
- Total Logs Processed: 4,195,338+
- Anomalies Detected: 22
- Alerts Sent: 22/22 (100% delivery rate)
- LLM Error Rate: 30%
- Pipeline Uptime: 100%

---

## 2. Architecture

### 2.1 Microservices (SAP Cloud Foundry)

**ETL Pipeline** (`soc-etl-pipeline`)
- Language: Python 3.10
- Polls SAP Log Ingestion API every 30 minutes
- Splits logs into SAP_SYSTEM_LOGS and SAP_LLM_LOGS
- Handles pagination (12 pages × 500 records = 5,700+ records per cycle)

**ML Engine** (`ml-engine`)
- Language: Python 3.10 + scikit-learn
- FastAPI REST service on port 8080
- 4 Isolation Forest models (SYSTEM/LLM × PEAK/OFFPEAK)
- Auto-trains on first boot if no artifacts present
- Scores 1,000 logs per API call

**Alerting Service** (`alerting-service`)
- Language: Python 3.10
- Daemon process polling every 60 seconds
- Reads IS_ANOMALY=TRUE from ANOMALY_RESULTS
- Creates INCIDENTS with severity classification
- POSTs structured WHAT/WHEN/WHY alerts to SAP API

**API Gateway** (`api-gateway`)
- Language: Python 3.10 + FastAPI
- Endpoints: /api/stats, /api/anomalies, /api/incidents, /api/logs
- CORS enabled for frontend connections
- Swagger UI at /docs

**React Dashboard** (`soc-frontend`)
- Framework: React 18 + Vite + Recharts + Tailwind CSS
- Auto-refreshes every 30 seconds
- KPI cards, anomaly timeline, incident table, LLM metrics

**Streamlit Dashboard** (`soc-streamlit`)
- Framework: Streamlit + Plotly
- 5 pages: Executive Overview, Incident Analysis, ML Performance, Log Analytics, Forensic Report
- Forensic incident reports with remediation steps

### 2.2 Database (SAP HANA Cloud)

| Table | Records | Purpose |
|-------|---------|---------|
| SAP_SYSTEM_LOGS | 2.4M+ | Raw system/security logs |
| SAP_LLM_LOGS | 1.7M+ | LLM interaction logs |
| ANOMALY_RESULTS | 8,000+ | ML scoring results |
| INCIDENTS | 22 | Confirmed threats with webhooks |

### 2.3 ML Methodology

**Algorithm:** Isolation Forest (unsupervised anomaly detection)

**Why Isolation Forest:**
- No labeled attack data required (unsupervised)
- Handles high-dimensional security log features
- Fast inference suitable for real-time scoring
- Configurable contamination rate per time band

**Feature Engineering:**
- System logs: HTTP status distribution, IP frequency, service patterns, time-based features
- LLM logs: Cost anomalies, response time spikes, error rate patterns, model usage shifts

**Training Strategy:**
- 4 model instances for peak/off-peak × system/LLM
- Peak hours (08:00-18:00): 2% contamination (stricter)
- Off-peak hours (18:00-08:00): 4% contamination (more lenient)
- Trained on 100K samples per model from HANA

---

## 3. Alert Format

Each alert sent to SAP API follows the WHAT/WHEN/WHY format:

```
WHAT: Anomalous system activity detected (type: Unknown).
WHEN: 2026-05-05T14:30:27Z.
WHY: ML model flagged with 35% anomaly confidence (source_id: 4715740).
```

---

## 4. Live URLs

| Dashboard | URL |
|-----------|-----|
| React Dashboard | https://soc-frontend.cfapps.us10-001.hana.ondemand.com |
| Streamlit Forensics | https://soc-streamlit.cfapps.us10-001.hana.ondemand.com |
| API Gateway | https://api-gateway.cfapps.us10-001.hana.ondemand.com |
| API Docs | https://api-gateway.cfapps.us10-001.hana.ondemand.com/docs |
| ML Engine | https://ml-engine.cfapps.us10-001.hana.ondemand.com |

---

## 5. How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- SAP HANA credentials
- SAP API Key

### Setup

```bash
# Clone repository
git clone https://github.com/Alanamtz06/SAP---AI-Security-Anomaly-Detection.git
cd SAP---AI-Security-Anomaly-Detection/sap-soc-hackathon

# Create backend .env
cat > backend/.env << EOF
HANA_HOST=bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASS=your_password_here
SAP_API_KEY=your_api_key_here
ML_ENGINE_URL=http://localhost:8001
ALERT_INTERVAL_SECONDS=60
POLL_INTERVAL_SECONDS=120
EOF
```

### Run Services

```bash
# Terminal 1: ML Engine
cd backend/services/ml-engine
pip install -r requirements.txt
python app.py

# Terminal 2: ETL Pipeline (manual run)
cd backend/services/etl-pipeline
pip install -r requirements.txt
python app.py

# Terminal 3: Alerting Service (manual run)
cd backend/services/alerting-service
pip install -r requirements.txt
python app.py

# Terminal 4: API Gateway
cd backend/services/api-gateway
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Terminal 5: Frontend
cd frontend
npm install
npm run dev

# Terminal 6: Streamlit
cd streamlit-dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## 6. Repository Structure

```
sap-soc-hackathon/
├── backend/
│   ├── database/          # HANA connection + SQL schemas
│   ├── notebooks/         # ML training notebooks
│   └── services/
│       ├── alerting-service/  # Webhook dispatcher
│       ├── api-gateway/       # REST API
│       ├── etl-pipeline/      # Log ingestion
│       └── ml-engine/         # Anomaly detection
├── docs/                  # Architecture + technical report
├── frontend/              # React dashboard
├── streamlit-dashboard/   # Forensic analysis dashboard
└── mta.yaml               # CF MTA deployment descriptor
```

---

## 7. Evaluation Criteria Coverage

| Criterion | Weight | Implementation |
|-----------|--------|---------------|
| Operational Efficiency (MTTD) | 40% | 60s alert latency, automated pipeline |
| SAP Ecosystem Integration | 25% | BTP + CF + HANA + SAC |
| Architecture & MLOps | 20% | 4 IF models, clean microservices, model versioning |
| Business Impact | 15% | Forensic reports, remediation steps, executive dashboards |
