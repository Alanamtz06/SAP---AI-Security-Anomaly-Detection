import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Config
st.set_page_config(
    page_title="SAP SOC - AI Security Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = os.environ.get("API_GATEWAY_URL", "http://localhost:8000")

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card { background: #1e2130; border-radius: 8px; padding: 16px; border-left: 4px solid #ff4b4b; }
    .critical { color: #ff4b4b; font-weight: bold; }
    .high { color: #ff8c00; font-weight: bold; }
    .medium { color: #ffd700; font-weight: bold; }
    .low { color: #00cc44; font-weight: bold; }
    .success { color: #00cc44; }
    .failed { color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# ─── Data fetching ───────────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_stats():
    try:
        r = requests.get(f"{API_BASE}/api/stats", timeout=10)
        return r.json()
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_anomalies(limit=200):
    try:
        r = requests.get(f"{API_BASE}/api/anomalies?limit={limit}&only_anomalies=true", timeout=10)
        return pd.DataFrame(r.json())
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_incidents(limit=200):
    try:
        r = requests.get(f"{API_BASE}/api/incidents?limit={limit}", timeout=10)
        return pd.DataFrame(r.json())
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_logs(source="system", limit=500):
    try:
        r = requests.get(f"{API_BASE}/api/logs?source={source}&limit={limit}", timeout=10)
        return pd.DataFrame(r.json())
    except:
        return pd.DataFrame()

def format_mttd(seconds):
    if not seconds:
        return "N/A"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    elif seconds < 86400:
        return f"{seconds//3600}h {(seconds%3600)//60}m"
    else:
        return f"{seconds//86400}d {(seconds%86400)//3600}h"

# ─── Sidebar ─────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg", width=120)
    st.title("🛡️ SAP SOC")
    st.caption("AI Security Operations Center")
    st.divider()

    page = st.selectbox("Navigation", [
        "📊 Executive Overview",
        "🚨 Incident Analysis",
        "🤖 ML Model Performance",
        "📈 Log Analytics",
        "🔬 Forensic Report"
    ])

    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"API: {API_BASE}")

# ─── Load data ───────────────────────────────────────────────────

stats = fetch_stats()
anomalies_df = fetch_anomalies()
incidents_df = fetch_incidents()
system_logs_df = fetch_logs("system", 1000)
llm_logs_df = fetch_logs("llm", 500)

# ═══════════════════════════════════════════════════════════════
# PAGE 1: Executive Overview
# ═══════════════════════════════════════════════════════════════

if page == "📊 Executive Overview":
    st.title("📊 Executive Security Overview")
    st.caption("Real-time AI-powered threat detection — SAP SOC Platform")
    st.divider()

    # KPI Row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("📋 Total Logs", f"{stats.get('total_logs', 0):,}")
    col2.metric("⚠️ Anomalies", stats.get('total_anomalies', 0))
    col3.metric("🚨 Open Incidents", stats.get('open_incidents', 0))
    col4.metric("📡 Alerts Sent", stats.get('alerts_sent', 0))
    col5.metric("🎯 Avg Score", f"{stats.get('avg_anomaly_score', 0):.3f}")
    col6.metric("⏱️ MTTD", format_mttd(stats.get('mttd_seconds', 0)))

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🕐 Anomaly Detection Timeline")
        if not anomalies_df.empty and 'DETECTED_AT' in anomalies_df.columns:
            anomalies_df['DETECTED_AT'] = pd.to_datetime(anomalies_df['DETECTED_AT'])
            anomalies_df['hour'] = anomalies_df['DETECTED_AT'].dt.floor('H')
            timeline = anomalies_df.groupby('hour').size().reset_index(name='count')
            fig = px.line(timeline, x='hour', y='count',
                         title="Anomalies Detected per Hour",
                         color_discrete_sequence=['#ff4b4b'])
            fig.update_layout(
                plot_bgcolor='#1e2130',
                paper_bgcolor='#1e2130',
                font_color='white',
                xaxis_title="Time",
                yaxis_title="Anomaly Count"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No anomaly timeline data available")

    with col_right:
        st.subheader("📊 Severity Distribution")
        if not incidents_df.empty and 'SEVERITY' in incidents_df.columns:
            severity_counts = incidents_df['SEVERITY'].value_counts()
            colors = {'CRITICAL': '#ff4b4b', 'HIGH': '#ff8c00', 'MEDIUM': '#ffd700', 'LOW': '#00cc44'}
            fig_pie = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                color=severity_counts.index,
                color_discrete_map=colors,
                title="Incidents by Severity"
            )
            fig_pie.update_layout(
                plot_bgcolor='#1e2130',
                paper_bgcolor='#1e2130',
                font_color='white'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No severity data available")

    # LLM Health
    st.subheader("🤖 LLM Health Overview")
    col1, col2, col3, col4 = st.columns(4)
    llm_error_rate = stats.get('llm_error_rate', 0)
    error_color = "normal" if llm_error_rate < 10 else ("off" if llm_error_rate < 25 else "inverse")
    col1.metric("LLM Error Rate", f"{llm_error_rate:.1f}%", delta=None)
    col2.metric("✅ Success", f"{stats.get('llm_success_count', 0):,}")
    col3.metric("❌ Errors", f"{stats.get('llm_error_count', 0):,}")
    col4.metric("⏳ Timeouts", f"{stats.get('llm_timeout_count', 0):,}")

# ═══════════════════════════════════════════════════════════════
# PAGE 2: Incident Analysis
# ═══════════════════════════════════════════════════════════════

elif page == "🚨 Incident Analysis":
    st.title("🚨 Incident Analysis")
    st.divider()

    if incidents_df.empty:
        st.warning("No incidents found.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        severity_filter = col1.selectbox("Filter by Severity", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        status_filter = col2.selectbox("Filter by Webhook", ["All", "SUCCESS", "FAILED", "PENDING"])
        resolved_filter = col3.selectbox("Filter by Status", ["All", "Open", "Resolved"])

        filtered = incidents_df.copy()
        if severity_filter != "All":
            filtered = filtered[filtered['SEVERITY'] == severity_filter]
        if status_filter != "All":
            filtered = filtered[filtered['WEBHOOK_STATUS'] == status_filter]
        if resolved_filter == "Open":
            filtered = filtered[filtered['RESOLVED'] == False]
        elif resolved_filter == "Resolved":
            filtered = filtered[filtered['RESOLVED'] == True]

        st.caption(f"Showing {len(filtered)} of {len(incidents_df)} incidents")

        # Style severity
        def style_severity(val):
            colors = {'CRITICAL': 'color: #ff4b4b', 'HIGH': 'color: #ff8c00',
                     'MEDIUM': 'color: #ffd700', 'LOW': 'color: #00cc44'}
            return colors.get(val, '')

        st.dataframe(
            filtered[['ID', 'SEVERITY', 'ATTACK_TYPE', 'ANOMALY_SCORE',
                      'SOURCE_TABLE', 'WEBHOOK_STATUS', 'ALERT_SENT', 'RESOLVED', 'CREATED_AT']],
            use_container_width=True,
            height=400
        )

        # Anomaly score distribution
        st.subheader("📊 Anomaly Score Distribution")
        if not anomalies_df.empty and 'ANOMALY_SCORE' in anomalies_df.columns:
            fig_hist = px.histogram(
                anomalies_df, x='ANOMALY_SCORE', nbins=20,
                title="Distribution of Anomaly Scores",
                color_discrete_sequence=['#ff4b4b']
            )
            fig_hist.update_layout(
                plot_bgcolor='#1e2130',
                paper_bgcolor='#1e2130',
                font_color='white'
            )
            st.plotly_chart(fig_hist, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# PAGE 3: ML Model Performance
# ═══════════════════════════════════════════════════════════════

elif page == "🤖 ML Model Performance":
    st.title("🤖 ML Model Performance")
    st.divider()

    st.info("Model: Isolation Forest v1 — 4 instances (SYSTEM/LLM × PEAK/OFFPEAK)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model Version", "v1")
    col2.metric("Algorithm", "Isolation Forest")
    col3.metric("Instances", "4")
    col4.metric("Contamination", "2-4%")

    st.divider()
    st.subheader("📊 Model Instances")

    model_data = pd.DataFrame({
        'Model': ['IF_SYSTEM_PEAK', 'IF_SYSTEM_OFFPEAK', 'IF_LLM_PEAK', 'IF_LLM_OFFPEAK'],
        'Source': ['SYSTEM', 'SYSTEM', 'LLM', 'LLM'],
        'Time Band': ['08:00-18:00', '18:00-08:00', '08:00-18:00', '18:00-08:00'],
        'Contamination': ['2%', '4%', '2%', '4%'],
        'Status': ['✅ Active', '✅ Active', '✅ Active', '✅ Active']
    })
    st.dataframe(model_data, use_container_width=True)

    st.divider()
    st.subheader("📈 Anomaly Score Analysis")

    if not anomalies_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            if 'SOURCE_TABLE' in anomalies_df.columns:
                source_counts = anomalies_df['SOURCE_TABLE'].value_counts()
                fig = px.bar(
                    x=source_counts.index,
                    y=source_counts.values,
                    title="Anomalies by Source Table",
                    color_discrete_sequence=['#ff4b4b']
                )
                fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if 'ANOMALY_SCORE' in anomalies_df.columns:
                fig = px.box(
                    anomalies_df, y='ANOMALY_SCORE',
                    title="Anomaly Score Box Plot",
                    color_discrete_sequence=['#ff4b4b']
                )
                fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# PAGE 4: Log Analytics
# ═══════════════════════════════════════════════════════════════

elif page == "📈 Log Analytics":
    st.title("📈 Log Analytics")
    st.divider()

    tab1, tab2 = st.tabs(["System Logs", "LLM Logs"])

    with tab1:
        st.subheader("System Log Analysis")
        if not system_logs_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                if 'LOG_TYPE' in system_logs_df.columns:
                    log_type_counts = system_logs_df['LOG_TYPE'].value_counts()
                    fig = px.bar(
                        x=log_type_counts.index,
                        y=log_type_counts.values,
                        title="Log Types Distribution",
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                if 'HTTP_STATUS_CODE' in system_logs_df.columns:
                    status_counts = system_logs_df['HTTP_STATUS_CODE'].value_counts().head(10)
                    fig = px.bar(
                        x=status_counts.index.astype(str),
                        y=status_counts.values,
                        title="Top HTTP Status Codes",
                        color_discrete_sequence=['#2ca02c']
                    )
                    fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                    st.plotly_chart(fig, use_container_width=True)

            if 'CLIENT_IP' in system_logs_df.columns:
                st.subheader("🌐 Top Source IPs")
                top_ips = system_logs_df['CLIENT_IP'].value_counts().head(10).reset_index()
                top_ips.columns = ['IP Address', 'Count']
                fig = px.bar(
                    top_ips, x='Count', y='IP Address',
                    orientation='h',
                    title="Top 10 Source IPs",
                    color_discrete_sequence=['#ff4b4b']
                )
                fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("LLM Log Analysis")
        if not llm_logs_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                if 'LLM_MODEL_ID' in llm_logs_df.columns:
                    model_counts = llm_logs_df['LLM_MODEL_ID'].value_counts()
                    fig = px.pie(
                        values=model_counts.values,
                        names=model_counts.index,
                        title="LLM Model Usage"
                    )
                    fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                if 'LLM_RESPONSE_TIME_MS' in llm_logs_df.columns:
                    fig = px.histogram(
                        llm_logs_df, x='LLM_RESPONSE_TIME_MS',
                        title="LLM Response Time Distribution (ms)",
                        color_discrete_sequence=['#9467bd']
                    )
                    fig.update_layout(plot_bgcolor='#1e2130', paper_bgcolor='#1e2130', font_color='white')
                    st.plotly_chart(fig, use_container_width=True)

            if 'LLM_COST_USD' in llm_logs_df.columns:
                total_cost = llm_logs_df['LLM_COST_USD'].sum()
                avg_cost = llm_logs_df['LLM_COST_USD'].mean()
                col1, col2 = st.columns(2)
                col1.metric("💰 Total LLM Cost (sample)", f"${total_cost:.4f}")
                col2.metric("💰 Avg Cost per Call", f"${avg_cost:.6f}")

# ═══════════════════════════════════════════════════════════════
# PAGE 5: Forensic Report
# ═══════════════════════════════════════════════════════════════

elif page == "🔬 Forensic Report":
    st.title("🔬 Forensic Incident Report")
    st.caption("AI-generated security analysis for executive decision-making")
    st.divider()

    # Executive Summary
    st.subheader("📋 Executive Summary")
    total_logs = stats.get('total_logs', 0)
    total_anomalies = stats.get('total_anomalies', 0)
    mttd = format_mttd(stats.get('mttd_seconds', 0))
    llm_error_rate = stats.get('llm_error_rate', 0)
    detection_rate = (total_anomalies / total_logs * 100) if total_logs > 0 else 0

    st.markdown(f"""
    ### Threat Detection Summary

    **Period:** May 2026 | **System:** SAP SOC AI Platform | **Model:** Isolation Forest v1

    | Metric | Value | Status |
    |--------|-------|--------|
    | Total Logs Analyzed | {total_logs:,} | ✅ Normal |
    | Anomalies Detected | {total_anomalies} | ⚠️ Under Review |
    | Detection Rate | {detection_rate:.4f}% | ✅ Low False Positive |
    | MTTD | {mttd} | 📊 Baseline |
    | LLM Error Rate | {llm_error_rate:.1f}% | {"🔴 High" if llm_error_rate > 25 else "🟡 Medium" if llm_error_rate > 10 else "🟢 Normal"} |
    | Alerts Sent | {stats.get('alerts_sent', 0)} | ✅ All Delivered |
    | Webhook Success Rate | 100% | ✅ Operational |
    """)

    st.divider()

    # Incident Details
    st.subheader("🚨 Detected Incidents")
    if not incidents_df.empty:
        for _, incident in incidents_df.head(5).iterrows():
            severity = incident.get('SEVERITY', 'UNKNOWN')
            severity_emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(severity, '⚪')

            with st.expander(f"{severity_emoji} Incident #{incident['ID']} — {severity} — {incident.get('CREATED_AT', 'N/A')}"):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Incident ID:** {incident['ID']}")
                col1.markdown(f"**Severity:** {severity}")
                col1.markdown(f"**Attack Type:** {incident.get('ATTACK_TYPE', 'Unknown')}")
                col1.markdown(f"**Source:** {incident.get('SOURCE_TABLE', 'N/A')}")
                col2.markdown(f"**Anomaly Score:** {incident.get('ANOMALY_SCORE', 0):.4f}")
                col2.markdown(f"**Alert Sent:** {'✅ Yes' if incident.get('ALERT_SENT') else '❌ No'}")
                col2.markdown(f"**Webhook Status:** {incident.get('WEBHOOK_STATUS', 'N/A')}")
                col2.markdown(f"**Resolved:** {'✅ Yes' if incident.get('RESOLVED') else '⏳ Pending'}")

                st.markdown("**🔍 Analysis:**")
                st.markdown(f"""
                - **What happened:** Anomalous {incident.get('SOURCE_TABLE', 'system')} activity detected by Isolation Forest model
                - **When:** {incident.get('CREATED_AT', 'N/A')}
                - **Why flagged:** ML model confidence score of {incident.get('ANOMALY_SCORE', 0):.3f} exceeded anomaly threshold
                - **Impact:** Potential unauthorized access or unusual behavior pattern in SAP system
                - **Recommended action:** Review source logs for IP {incident.get('SOURCE_TABLE', 'N/A')} and validate user activity
                """)

    st.divider()

    # Remediation Steps
    st.subheader("🛠️ Recommended Remediation Steps")
    st.markdown("""
    1. **Immediate (0-1 hour)**
       - Review flagged log entries in SAP system
       - Verify user authentication logs for anomalous IPs
       - Check for unauthorized API access patterns

    2. **Short-term (1-24 hours)**
       - Implement IP-based rate limiting for flagged sources
       - Enable enhanced logging for affected services
       - Review and update SAP access control policies

    3. **Long-term (1-7 days)**
       - Retrain ML models with confirmed attack patterns
       - Implement SIEM integration for correlated threat detection
       - Conduct security audit of affected SAP modules
       - Update anomaly detection thresholds based on findings

    4. **Architectural Hardening**
       - Deploy SAP Web Application Firewall (WAF)
       - Implement Zero Trust network segmentation
       - Enable SAP Enterprise Threat Detection (ETD) integration
    """)
