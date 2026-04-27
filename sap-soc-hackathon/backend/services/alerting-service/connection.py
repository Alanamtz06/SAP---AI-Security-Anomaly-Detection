import os
import json
from hdbcli import dbapi

_HOST = "bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com"
_PORT = 443
_USER = "DBADMIN"
# HANA_PASS env var overrides the local default — set it in .env or CF env
_PASS = os.environ.get("HANA_PASS", "Alana1234")


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
                sslValidateCertificate=False,
            )
    return dbapi.connect(
        address=_HOST,
        port=_PORT,
        user=_USER,
        password=_PASS,
        encrypt=True,
        sslValidateCertificate=False,
    )


def test_connection():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM DUMMY")
        conn.close()
        print("[db] HANA connection OK")
    except Exception as exc:
        print(f"[db] HANA connection FAILED: {exc}")
        raise
