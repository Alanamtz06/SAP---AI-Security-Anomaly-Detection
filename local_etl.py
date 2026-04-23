"""
local_etl.py — SAP SOC Hackathon local runner
Descarga logs cada 5 min de la API, los respalda en CSV y los inserta a HANA Cloud.
Corre en tu máquina local (no requiere Cloud Foundry).

Uso:
    python local_etl.py

Requisitos en .env:
    HANA_PASS=tu_contraseña
    SAP_API_KEY=tu_api_key
"""

import os
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv
from hdbcli import dbapi

# Carga variables de .env ANTES de leer os.environ
load_dotenv()

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

HANA_HOST = "bdad283d-c94e-46fb-8167-78fba6c2018a.hna1.prod-us10.hanacloud.ondemand.com"
HANA_PORT = 443
HANA_USER = "DBADMIN"

BASE_URL = "https://sap-api-b2.679186.xyz"

POLL_INTERVAL      = 300   # segundos entre cada descarga (5 min)
KEEPALIVE_INTERVAL = 300   # segundos entre cada ping a HANA (5 min)

BACKUP_DIR = Path("logs_backup")

# Tipos de log que van a la tabla SAP_LLM_LOGS
LLM_TYPES = {"LLM_REQUEST", "LLM_ERROR", "LLM_TIMEOUT"}

# ─── SQL (append-only, sin force=True ni DROP) ────────────────────────────────

INSERT_SYSTEM = """
INSERT INTO DBADMIN.SAP_SYSTEM_LOGS
    (TIMESTAMP, LOG_TYPE, HTTP_STATUS_CODE, CLIENT_IP, SERVICE_ID, WINDOW_START)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_LLM = """
INSERT INTO DBADMIN.SAP_LLM_LOGS
    (TIMESTAMP, LOG_TYPE, LLM_MODEL_ID, LLM_STATUS, LLM_COST_USD, LLM_RESPONSE_TIME_MS, WINDOW_START)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

# ─── HELPERS DE TIEMPO ────────────────────────────────────────────────────────

def now_str() -> str:
    """Timestamp local legible para logs."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(ts_str):
    """Convierte string ISO 8601 a datetime naive (sin tz) para HANA."""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(
            str(ts_str).replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


# ─── HELPERS DE TIPOS ─────────────────────────────────────────────────────────

def _val(v):
    """Convierte string vacío o None a None."""
    return None if (v is None or str(v).strip() == "" or str(v) == "nan") else v


def _int_val(v):
    """Convierte '200.0' → 200, o retorna None."""
    v = _val(v)
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _float_val(v):
    """Convierte a float, o retorna None."""
    v = _val(v)
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ─── CONEXIÓN HANA ────────────────────────────────────────────────────────────

def get_connection() -> dbapi.Connection:
    """
    Crea una conexión fresca a HANA.
    En Cloud Foundry usa VCAP_SERVICES; local usa HANA_PASS del .env.
    """
    import json
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
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=os.environ["HANA_PASS"],  # viene del .env, nunca hardcodeado
        encrypt=True,
        sslValidateCertificate=False,
    )


# ─── KEEP-ALIVE (thread separado) ─────────────────────────────────────────────

def _keep_alive_worker():
    """
    Hilo daemon: cada KEEPALIVE_INTERVAL segundos hace SELECT 1 FROM DUMMY.
    Mantiene viva la sesión del trial de HANA Cloud.
    Falla silenciosamente — no detiene el loop principal.
    """
    while True:
        time.sleep(KEEPALIVE_INTERVAL)
        ts = now_str()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUMMY")
            conn.close()
            print(f"[{ts}] [KEEP-ALIVE] HANA ping OK")
        except Exception as exc:
            # Solo loguea — nunca detiene el proceso principal
            print(f"[{ts}] [KEEP-ALIVE] HANA ping FAILED: {exc}")


def start_keep_alive():
    t = threading.Thread(target=_keep_alive_worker, daemon=True, name="hana-keepalive")
    t.start()
    print(f"[{now_str()}] [KEEP-ALIVE] Hilo iniciado (cada {KEEPALIVE_INTERVAL}s)")


# ─── API: DESCARGA DE LOGS ────────────────────────────────────────────────────

def _get_headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['SAP_API_KEY']}"}


def fetch_logs() -> tuple[str, list[dict]]:
    """
    1. GET /info → obtiene total_pages y window_start.
    2. GET /logs/current?page=N para cada página.
    Retorna (window_start_iso_str, lista_de_logs).
    """
    headers = _get_headers()

    resp = requests.get(f"{BASE_URL}/info", headers=headers, timeout=15)
    resp.raise_for_status()
    info = resp.json()

    total_pages  = int(info.get("total_pages", 1))
    window_start = str(info.get("window_start", ""))

    print(f"[{now_str()}] API /info → total_pages={total_pages}, window_start={window_start}")

    all_logs: list[dict] = []
    for page in range(1, total_pages + 1):
        r = requests.get(
            f"{BASE_URL}/logs/current",
            headers=headers,
            params={"page": page},
            timeout=30,
        )
        r.raise_for_status()
        page_data = r.json().get("data", [])
        all_logs.extend(page_data)
        print(f"[{now_str()}]   Página {page}/{total_pages}: {len(page_data)} registros")

    return window_start, all_logs


# ─── CSV BACKUP ───────────────────────────────────────────────────────────────

def _safe_filename(window_start: str) -> str:
    """Convierte timestamp ISO a nombre de archivo seguro (sin ':')."""
    return window_start.replace(":", "-").replace(" ", "T")


def save_csv(window_start: str, logs: list[dict]) -> Path:
    """
    Guarda los logs en logs_backup/{window_start}.csv ANTES de insertar.
    Añade columna _window_start para poder reintentar sin perder el contexto.
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    path = BACKUP_DIR / f"{_safe_filename(window_start)}.csv"
    df = pd.DataFrame(logs)
    df["_window_start"] = window_start  # metadato para retry
    df.to_csv(path, index=False)
    print(f"[{now_str()}] CSV guardado: {path} ({len(logs)} filas)")
    return path


def _marker_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".inserted")


def is_inserted(csv_path: Path) -> bool:
    return _marker_path(csv_path).exists()


def mark_as_inserted(csv_path: Path):
    _marker_path(csv_path).write_text(datetime.now().isoformat())


# ─── INSERCIÓN A HANA ─────────────────────────────────────────────────────────

def _build_rows(logs: list[dict], window_start_str: str) -> tuple[list, list]:
    """
    Clasifica logs en system vs LLM y construye las tuplas para executemany.
    - System logs: llm_* son NULL
    - LLM logs:    service_id/client_ip/http_status_code son NULL
    """
    window_dt = _parse_ts(window_start_str)
    system_rows: list[tuple] = []
    llm_rows:    list[tuple] = []

    for log in logs:
        log_type = _val(log.get("sap_function_log_type")) or "INFO"
        ts       = _parse_ts(log.get("@timestamp"))

        if log_type in LLM_TYPES:
            # LLM log — columnas de sistema son NULL implícitamente
            llm_rows.append((
                ts,
                log_type,
                _val(log.get("llm_model_id")),
                _val(log.get("llm_status")),
                _float_val(log.get("llm_cost_usd")),
                _int_val(log.get("llm_response_time_ms")),
                window_dt,
            ))
        else:
            # System log — columnas LLM son NULL implícitamente
            system_rows.append((
                ts,
                log_type,
                _int_val(log.get("http_status_code")),
                _val(log.get("client_ip")),
                _val(log.get("service_id")),
                window_dt,
            ))

    return system_rows, llm_rows


def insert_to_hana(logs: list[dict], window_start_str: str):
    """
    Inserta logs en HANA usando append-only (INSERT, sin force=True ni DROP).
    Lanza excepción si falla — el caller decide si marcar el CSV como fallido.
    """
    system_rows, llm_rows = _build_rows(logs, window_start_str)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if system_rows:
            cursor.executemany(INSERT_SYSTEM, system_rows)
            print(f"[{now_str()}] Insertados {len(system_rows)} system logs")
        if llm_rows:
            cursor.executemany(INSERT_LLM, llm_rows)
            print(f"[{now_str()}] Insertados {len(llm_rows)} LLM logs")
        conn.commit()
        print(f"[{now_str()}] HANA commit OK")
    except Exception:
        conn.rollback()
        raise  # propaga para que el caller lo capture
    finally:
        conn.close()


# ─── RETRY: CSVs PENDIENTES AL ARRANQUE ───────────────────────────────────────

def retry_pending_csvs():
    """
    Al iniciar, busca CSV sin archivo .inserted y reintenta la inserción.
    Permite recuperar datos si el proceso anterior falló o fue interrumpido.
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    pending = sorted(
        p for p in BACKUP_DIR.glob("*.csv") if not is_inserted(p)
    )

    if not pending:
        print(f"[{now_str()}] Sin CSVs pendientes de reintentar.")
        return

    print(f"[{now_str()}] {len(pending)} CSV(s) pendiente(s) — reintentando...")
    for csv_path in pending:
        print(f"[{now_str()}]   Reintentando: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            # Extrae window_start de la columna que guardamos al crear el CSV
            window_start_str = ""
            if "_window_start" in df.columns:
                vals = df["_window_start"].dropna()
                if not vals.empty:
                    window_start_str = str(vals.iloc[0])
            logs = df.to_dict("records")
            insert_to_hana(logs, window_start_str)
            mark_as_inserted(csv_path)
            print(f"[{now_str()}]   OK: {csv_path}")
        except Exception as exc:
            print(f"[{now_str()}]   FALLÓ {csv_path}: {exc}")
            # Continúa con el siguiente — no detiene el arranque


# ─── CICLO PRINCIPAL ──────────────────────────────────────────────────────────

def run_cycle():
    """
    Un ciclo completo:
    1. Descarga logs de la API
    2. Guarda CSV de respaldo (ANTES de insertar)
    3. Inserta en HANA
    4. Marca CSV como insertado
    Si HANA falla, el CSV queda sin marcar y se reintentará al próximo reinicio.
    """
    print(f"\n[{now_str()}] ──── Inicio de ciclo ────")

    # 1. Descarga
    window_start, logs = fetch_logs()
    print(f"[{now_str()}] Total descargados: {len(logs)} logs (window={window_start})")

    if not logs:
        print(f"[{now_str()}] Sin logs nuevos, saltando ciclo.")
        return

    # 2. CSV backup — siempre antes de tocar HANA
    csv_path = save_csv(window_start, logs)

    # 3. Insertar a HANA
    try:
        insert_to_hana(logs, window_start)
        # 4. Marcar como exitoso solo si la inserción fue bien
        mark_as_inserted(csv_path)
        print(f"[{now_str()}] Ciclo completo: {len(logs)} filas insertadas.")
    except Exception as exc:
        # Error no fatal: solo loguea. El CSV queda sin .inserted para retry.
        print(f"[{now_str()}] ERROR insertando en HANA: {exc}")
        print(f"[{now_str()}] El respaldo CSV está en: {csv_path}")
        print(f"[{now_str()}] Se reintentará automáticamente al próximo reinicio.")


# ─── ENTRADA PRINCIPAL ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  SAP SOC Hackathon — Local ETL Runner")
    print(f"  Iniciado: {now_str()}")
    print("=" * 60)

    # Validar variables de entorno obligatorias
    for var in ("HANA_PASS", "SAP_API_KEY"):
        if not os.environ.get(var):
            sys.exit(f"ERROR: {var} no está definida. Agrégala a tu archivo .env")

    # Probar conexión a HANA antes de arrancar
    print(f"[{now_str()}] Probando conexión a HANA...")
    try:
        _conn = get_connection()
        _conn.cursor().execute("SELECT 1 FROM DUMMY")
        _conn.close()
        print(f"[{now_str()}] Conexión HANA OK")
    except Exception as e:
        sys.exit(f"ERROR: No se pudo conectar a HANA: {e}")

    # Reintentar CSVs sin insertar de ejecuciones anteriores
    retry_pending_csvs()

    # Iniciar hilo de keep-alive en paralelo
    start_keep_alive()

    # Loop principal de descarga e inserción
    print(f"[{now_str()}] Loop principal iniciado (cada {POLL_INTERVAL}s).")
    print(f"[{now_str()}] Presiona Ctrl+C para detener.\n")

    while True:
        try:
            run_cycle()
        except KeyboardInterrupt:
            print(f"\n[{now_str()}] Detenido por el usuario.")
            sys.exit(0)
        except Exception as exc:
            # Error inesperado (red, API caída, etc.) — loguea y sigue
            print(f"[{now_str()}] ERROR inesperado en ciclo: {exc}")
            print(f"[{now_str()}] Reintentando en {POLL_INTERVAL}s...")

        time.sleep(POLL_INTERVAL)
