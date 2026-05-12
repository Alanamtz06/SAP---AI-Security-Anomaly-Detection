# SAP SOC — AI Security Anomaly Detection
**Team CTRL_C_CTRL_V | SAP x Tec de Monterrey Hackathon 2026**

## Live Dashboards

| Dashboard | URL |
|-----------|-----|
| React Dashboard | https://soc-frontend.cfapps.us10-001.hana.ondemand.com |
| Streamlit Forensics | https://soc-streamlit.cfapps.us10-001.hana.ondemand.com |
| API Gateway | https://api-gateway.cfapps.us10-001.hana.ondemand.com |
| API Docs | https://api-gateway.cfapps.us10-001.hana.ondemand.com/docs |

## Deliverables
- [Architecture Diagram](sap-soc-hackathon/docs/architecture_diagram.md)
- [Technical Report](sap-soc-hackathon/docs/technical_report.md)

## Architecture
Real-time AI-powered SOC platform on SAP BTP Cloud Foundry:
- **ETL Pipeline**: Ingests 5,700+ logs every 30 min from SAP API
- **ML Engine**: 4 Isolation Forest models detecting anomalies in real-time
- **Alerting Service**: Sends automated WHAT/WHEN/WHY alerts within 60 seconds
- **API Gateway**: REST API exposing all data to dashboards
- **React Dashboard**: Real-time KPIs, anomaly timeline, incident table
- **Streamlit Dashboard**: 5-page forensic analysis with remediation steps

## Live Metrics
- 4.2M+ logs processed
- 22 anomalies detected
- 22/22 alerts delivered (100% success rate)
- 30% LLM error rate detected

## Tech Stack
Python 3.10 · scikit-learn · FastAPI · React 18 · Streamlit · SAP HANA Cloud · SAP Cloud Foundry · SAP Analytics Cloud
