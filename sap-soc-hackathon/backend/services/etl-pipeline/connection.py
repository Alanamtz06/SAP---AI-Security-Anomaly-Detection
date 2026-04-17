import os
import json
from hdbcli import dbapi

HANA_LOCAL = {
    "host": "bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com",
    "port": 443,
    "user": "DBADMIN",
    "password": "Alana1234",
    "encrypt": True,
    "sslValidateCertificate": False
}


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
        address=HANA_LOCAL["host"],
        port=HANA_LOCAL["port"],
        user=HANA_LOCAL["user"],
        password=HANA_LOCAL["password"],
        encrypt=HANA_LOCAL["encrypt"],
        sslValidateCertificate=HANA_LOCAL["sslValidateCertificate"]
    )


def get_cursor():
    conn = get_connection()
    return conn, conn.cursor()


def execute_query(sql: str, params: list = None) -> list:
    conn, cursor = get_cursor()
    cursor.execute(sql, params or [])
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def execute_insert(sql: str, rows: list):
    conn, cursor = get_cursor()
    try:
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
        print("HANA connection OK")
        conn.close()
    except Exception as e:
        print(f"HANA connection FAILED: {e}")
