import os
import json
from hdbcli import dbapi


def get_connection():
    vcap_raw = os.environ.get("VCAP_SERVICES")
    if vcap_raw:
        vcap = json.loads(vcap_raw)
        if "hana" in vcap:
            creds = vcap["hana"][0]["credentials"]
            return dbapi.connect(
                address=creds["host"],
                port=int(creds["port"]),
                user=creds["user"],
                password=creds["password"],
                encrypt=True,
                sslValidateCertificate=False
            )
    return dbapi.connect(
        address=os.environ.get("HANA_HOST", "bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com"),
        port=int(os.environ.get("HANA_PORT", 443)),
        user=os.environ.get("HANA_USER", "DBADMIN"),
        password=os.environ.get("HANA_PASS", ""),
        encrypt=True,
        sslValidateCertificate=False
    )


def execute_query(sql: str, params=None) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        columns: list[str] = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def execute_insert(sql: str, rows: list):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, rows)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUMMY")
        conn.close()
        print("HANA connection OK")
        return True
    except Exception as e:
        print(f"HANA connection FAILED: {e}")
        return False
