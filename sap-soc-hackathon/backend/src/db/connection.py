import os
import json
from hdbcli import dbapi
import pandas as pd

def get_hana_credentials():
    """Obtiene credenciales de VCAP_SERVICES o variables locales"""
    vcap_raw = os.environ.get("VCAP_SERVICES")
    if vcap_raw:
        vcap = json.loads(vcap_raw)
        if "hana" in vcap:
            creds = vcap["hana"][0]["credentials"]
            return {
                "host": creds["host"],
                "port": int(creds["port"]),
                "user": creds["user"],
                "password": creds["password"],
            }
    
    # Local mode
    return {
        "host": "bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com",
        "port": 443,
        "user": "DBADMIN",
        "password": os.environ.get("HANA_PASS", ""),
    }

def get_connection():
    """Abre conexión fresca a HANA"""
    creds = get_hana_credentials()
    return dbapi.connect(
        address=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        encrypt=True,
        sslValidateCertificate=False
    )

def execute_query(sql: str) -> list:
    """Ejecuta query y retorna lista de dicts"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

def read_sql(sql: str) -> pd.DataFrame:
    """Lee SQL directamente a pandas DataFrame"""
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def test_connection():
    """Test de conexión"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        print("✓ HANA connection OK")
        return True
    except Exception as e:
        print(f"✗ HANA connection FAILED: {e}")
        return False