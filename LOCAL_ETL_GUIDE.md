# Local ETL Runner — Guía Completa

> **SAP x Tec de Monterrey SOC Hackathon**
> Script: `local_etl.py` | Autor: equipo SOC | Última actualización: 2026-04-23

---

## 1. Qué hace `local_etl.py`

`local_etl.py` es un **proceso de ingesta continuo** que corre en tu máquina local (Mini PC, laptop, etc.) y actúa como puente entre la API de logs del hackathon y tu base de datos HANA Cloud. Su función principal es descargar cada cinco minutos todos los registros disponibles en la ventana de tiempo activa de la API (`/logs/current`) y persistirlos en las tablas `SAP_SYSTEM_LOGS` y `SAP_LLM_LOGS` mediante instrucciones `INSERT` de solo adición, sin tocar ni borrar datos existentes.

El script incluye un **sistema de respaldo en CSV**: antes de intentar cualquier escritura en HANA, guarda el batch completo en `logs_backup/{window_start}.csv`. Esto garantiza que ningún dato se pierde si la conexión a HANA falla, si el proceso es interrumpido o si la red cae. Cada CSV lleva un archivo marcador `.inserted` que se crea **únicamente** después de un commit exitoso en HANA. Al reiniciar, el script detecta automáticamente cualquier CSV sin marcador y reintenta su inserción.

Para evitar que las conexiones al trial gratuito de HANA Cloud se cierren por inactividad, el script lanza un **hilo de keep-alive** que corre en paralelo y ejecuta `SELECT 1 FROM DUMMY` cada cinco minutos. Este hilo es un daemon independiente: si falla, solo registra el error en consola y continúa; nunca detiene el loop principal de descarga. Esto es especialmente importante en trials de SAP BTP donde las conexiones inactivas pueden expirar en minutos.

La **clasificación de logs** se hace en tiempo de inserción: si el campo `sap_function_log_type` es `LLM_REQUEST`, `LLM_ERROR` o `LLM_TIMEOUT`, el registro va a `SAP_LLM_LOGS` con las columnas de sistema (`service_id`, `client_ip`, `http_status_code`) como `NULL`. Cualquier otro tipo va a `SAP_SYSTEM_LOGS` con las columnas LLM (`llm_model_id`, `llm_status`, `llm_cost_usd`, `llm_response_time_ms`) como `NULL`. Este patrón de nulos es el mismo que usa el pipeline en Cloud Foundry.

---

## 2. Cómo funciona

### Flujo de arranque

```text
python local_etl.py
        │
        ├─ Carga .env  (HANA_PASS, SAP_API_KEY)
        ├─ Valida que ambas variables existan → sys.exit si falta alguna
        ├─ Prueba conexión: SELECT 1 FROM DUMMY
        │       └─ sys.exit si falla (no tiene sentido arrancar sin DB)
        │
        ├─ retry_pending_csvs()
        │       └─ Busca logs_backup/*.csv sin su .inserted
        │               └─ Por cada CSV pendiente:
        │                       ├─ Lee CSV con pandas
        │                       ├─ Extrae window_start de columna _window_start
        │                       ├─ Inserta en HANA
        │                       └─ Si OK → crea .inserted | Si falla → loguea y sigue
        │
        ├─ start_keep_alive()
        │       └─ Lanza threading.Thread(daemon=True)
        │               └─ Loop: sleep(300) → SELECT 1 FROM DUMMY → log resultado
        │
        └─ Loop principal
```

### Ciclo de descarga (cada 5 minutos)

```text
run_cycle()
    │
    ├─ 1. GET /info
    │       └─ total_pages, window_start
    │
    ├─ 2. GET /logs/current?page=1 ... ?page=N
    │       └─ Acumula todos los registros en memoria
    │
    ├─ 3. save_csv(window_start, logs)
    │       ├─ Añade columna _window_start a cada fila
    │       └─ Escribe logs_backup/{window_start}.csv
    │             (SIEMPRE, antes de tocar HANA)
    │
    ├─ 4. insert_to_hana(logs, window_start)
    │       ├─ Clasifica → system_rows[] / llm_rows[]
    │       ├─ cursor.executemany(INSERT_SYSTEM, system_rows)
    │       ├─ cursor.executemany(INSERT_LLM, llm_rows)
    │       ├─ conn.commit()
    │       └─ Si falla → rollback → lanza excepción
    │
    └─ 5. Si commit OK  → mark_as_inserted() (crea .inserted)
          Si commit FAIL → loguea error, CSV queda sin .inserted
                           → retry automático al próximo reinicio
```

### Paralelismo

```text
Proceso principal                 Hilo keep-alive (daemon)
─────────────────────────         ───────────────────────────
T+0    run_cycle()                T+0    start (lanza thread)
T+5    sleep...                   T+5    SELECT 1 FROM DUMMY → "ping OK"
T+5    run_cycle()                T+10   SELECT 1 FROM DUMMY → "ping OK"
T+10   sleep...                   ...
```

Los dos corren independientemente. El hilo daemon se termina automáticamente cuando el proceso principal finaliza o recibe `Ctrl+C`.

---

## 3. Instrucciones paso a paso

### 3a. Preparar el entorno

**Requisitos previos:**

- Python 3.10 o superior
- Acceso a internet desde la Mini PC
- Cuenta en SAP BTP con HANA Cloud activa

**Paso 1 — Instalar dependencias:**

```bash
# Desde la raíz del proyecto
pip install hdbcli requests pandas python-dotenv
```

O usando el requirements.txt del pipeline:

```bash
pip install -r sap-soc-hackathon/backend/services/etl-pipeline/requirements.txt
```

**Paso 2 — Crear el archivo `.env`** en la raíz del proyecto (mismo directorio que `local_etl.py`):

```env
HANA_PASS=tu_contraseña_real_aqui
SAP_API_KEY=ctrl-c-ctrl-v-2026-7a1b6c2d8e5f0g3h9i4j7k2l8m5n
```

> **Importante:** el `.env` ya debería estar en `.gitignore`. Verifica con `git status` antes de hacer commit que no aparezca listado.

**Paso 3 — Verificar la estructura:**

```text
proyecto/
├── local_etl.py        ← script principal
├── .env                ← credenciales (NO commitear)
├── logs_backup/        ← se crea automáticamente al correr
└── ...
```

---

### 3b. Lanzarlo en background (Mini PC — Linux/macOS)

**Opción A — `screen` (recomendado, puedes reconectarte):**

```bash
# Crear sesión nombrada
screen -S soc-etl

# Dentro del screen, lanzar el script
cd /ruta/al/proyecto
python local_etl.py

# Desconectarse SIN matar el proceso: Ctrl+A  luego  D
# Reconectarse después:
screen -r soc-etl

# Ver sesiones activas:
screen -ls
```

**Opción B — `nohup` (más simple, salida a archivo):**

```bash
cd /ruta/al/proyecto
nohup python local_etl.py > etl.log 2>&1 &

# El PID se imprime en consola, guardarlo:
echo $! > etl.pid

# Ver el log en tiempo real:
tail -f etl.log
```

**Opción C — Mini PC Windows (PowerShell):**

```powershell
# En una ventana de PowerShell minimizada
cd C:\ruta\al\proyecto
python local_etl.py
```

O como job en background:

```powershell
Start-Process python -ArgumentList "local_etl.py" -WorkingDirectory "C:\ruta\al\proyecto" -RedirectStandardOutput "etl.log" -WindowStyle Hidden
```

---

### 3c. Cómo evitar duplicados

Este es el punto más crítico. Hay tres situaciones:

#### Antes de lanzar `local_etl.py` por primera vez

1. **Verifica que no haya otro proceso de ingesta corriendo:**

```bash
# En Linux
ps aux | grep "local_etl\|etl-pipeline\|app.py"

# En Windows PowerShell
Get-Process python
```

1. **Verifica el estado actual de las tablas** (ejecuta en SAP HANA Database Explorer o con Python):

```python
# quick_check.py — corre esto ANTES de lanzar
from sap_soc_hackathon.backend.services.etl_pipeline.connection import execute_query
print(execute_query("SELECT COUNT(*) AS N, MAX(WINDOW_START) AS LAST FROM DBADMIN.SAP_SYSTEM_LOGS"))
print(execute_query("SELECT COUNT(*) AS N, MAX(WINDOW_START) AS LAST FROM DBADMIN.SAP_LLM_LOGS"))
```

1. Anota los conteos actuales como referencia.

#### Durante Fase 0–2 (recolección de datos / training)

| Situación | Acción |
| --------- | ------ |
| `local_etl.py` corriendo | OK — no toques nada más |
| Pipeline CF (`app.py`) desplegado en BTP | **Páusalo o elimínalo** — si ambos corren, duplicarás cada ventana |
| Reiniciar `local_etl.py` | OK — el retry de CSVs evita reinserciones, PERO lee la nota abajo |
| Misma ventana de tiempo, mismo CSV ya marcado | Seguro — `.inserted` existe, no reintenta |
| Misma ventana, CSV no marcado (crash a mitad) | Reintenta — puede ocurrir inserción parcial si el primer intento hizo commit parcial |

> **Nota sobre reinicio rápido:** Si reinicias el script dentro de la misma ventana de 5 minutos que la API devuelve, el script descargará los **mismos logs de nuevo** y generará un CSV nuevo. Para ventanas ya insertadas correctamente, los `.inserted` markers protegen los CSVs viejos, pero el nuevo batch del ciclo actual puede generar duplicados en HANA si la ventana no avanzó.
>
> **Solución práctica:** Si HANA no tiene clave única natural (PRIMARY KEY) en las tablas, **no reinicies el script hasta que la ventana actual haya rotado** (espera 5 minutos). Si tienes una clave única, los duplicados fallarán con "duplicate key" y se ignorarán.

#### Cuando pases a Fase 3 (producción en Cloud Foundry)

1. **Para `local_etl.py` primero:**

```bash
# screen:
screen -r soc-etl
# Ctrl+C dentro del screen

# nohup:
kill $(cat etl.pid)
```

1. **Espera a que la API avance a la próxima ventana** (máximo 5 minutos).

1. **Despliega el pipeline en CF:**

```bash
cd sap-soc-hackathon/backend/services/etl-pipeline
cf push
```

1. **Verifica los conteos** antes y después del primer ciclo en CF para confirmar que no hay duplicados.

> **Nunca corras `local_etl.py` y el pipeline CF al mismo tiempo sobre las mismas tablas.**

---

### 3d. Monitorear que funciona

**Ver logs en tiempo real:**

```bash
# screen: reconectar y ver salida directa
screen -r soc-etl

# nohup:
tail -f etl.log

# Buscar errores:
grep -i "error\|fail\|failed" etl.log
```

**Verificar CSVs generados:**

```bash
ls -lh logs_backup/
# Deberías ver un .csv y su .inserted por cada ciclo exitoso:
# 2026-04-23T15-00-00Z.csv
# 2026-04-23T15-00-00Z.inserted
# 2026-04-23T15-05-00Z.csv
# 2026-04-23T15-05-00Z.inserted
```

**Verificar datos en HANA** (cada ~30 minutos):

```sql
SELECT COUNT(*), MAX(WINDOW_START)
FROM DBADMIN.SAP_SYSTEM_LOGS
WHERE WINDOW_START > ADD_SECONDS(NOW(), -3600);

SELECT COUNT(*), MAX(WINDOW_START)
FROM DBADMIN.SAP_LLM_LOGS
WHERE WINDOW_START > ADD_SECONDS(NOW(), -3600);
```

**Señales de que todo va bien:**

- Un `.csv` + `.inserted` por cada ventana de 5 minutos
- Los logs imprimen `[KEEP-ALIVE] HANA ping OK` cada 5 minutos
- Los conteos en HANA crecen ~150-500 filas por ciclo

---

### 3e. Cómo parar el script

```bash
# Si está en screen:
screen -r soc-etl
# Luego Ctrl+C → el script imprime "Detenido por el usuario." y termina limpio

# Si está en nohup:
kill $(cat etl.pid)
# o:
kill $(pgrep -f local_etl.py)

# Windows:
# Ctrl+C en la ventana de PowerShell
# o desde Task Manager → busca python.exe
```

> El `Ctrl+C` está manejado con `except KeyboardInterrupt` — el proceso termina ordenadamente sin dejar conexiones HANA abiertas.

---

### 3f. Qué hacer si falla — CSV recovery

Si el script falló después de guardar el CSV pero antes de insertar en HANA, el CSV queda **sin su archivo `.inserted`**. Al reiniciar, se recupera automáticamente:

```bash
# Ver qué CSVs están pendientes:
ls logs_backup/*.csv | while read f; do
  marker="${f%.csv}.inserted"
  [ ! -f "$marker" ] && echo "PENDIENTE: $f"
done

# Simplemente reiniciar el script recupera todo:
python local_etl.py
# → "3 CSV(s) pendiente(s) — reintentando..."
```

**Si quieres recuperar manualmente un CSV específico:**

```python
import pandas as pd
from local_etl import insert_to_hana, mark_as_inserted
from pathlib import Path

csv_path = Path("logs_backup/2026-04-23T15-00-00Z.csv")
df = pd.read_csv(csv_path)
window_start = df["_window_start"].iloc[0]
logs = df.to_dict("records")
insert_to_hana(logs, window_start)
mark_as_inserted(csv_path)
print("Recuperado OK")
```

**Si quieres limpiar CSVs viejos ya insertados** (para liberar espacio):

```bash
# Elimina solo los que tienen su .inserted (ya están en HANA)
cd logs_backup
for f in *.inserted; do
  base="${f%.inserted}"
  rm -f "$base.csv" "$f"
  echo "Limpiado: $base"
done
```

---

## 4. Tabla de errores comunes

| Error | Causa probable | Solución |
| ----- | -------------- | -------- |
| `ERROR: HANA_PASS no está definida` | El archivo `.env` no existe, está en otro directorio, o la variable está mal escrita | Verifica que `.env` esté en el mismo directorio que `local_etl.py`. Revisa que no tenga espacios: `HANA_PASS=valor` (sin espacios alrededor del `=`) |
| `ERROR: No se pudo conectar a HANA: connection refused` o `timeout` | HANA Cloud está apagada (inactividad del trial), la IP de tu máquina no está en la allowlist de HANA, o el puerto 443 está bloqueado por firewall | Ve a SAP BTP Cockpit → HANA Cloud → Start instance. Verifica en "Connections" que tu IP esté permitida. |
| `requests.exceptions.HTTPError: 401 Unauthorized` | `SAP_API_KEY` incorrecta o expirada | Verifica el valor en `.env`. Prueba manualmente: `curl -H "Authorization: Bearer TU_KEY" https://sap-api-b2.679186.xyz/health` |
| `requests.exceptions.HTTPError: 429 Too Many Requests` | Estás llamando a la API más rápido de lo permitido | El script ya tiene 5 min entre ciclos. Si ocurre durante el fetch de páginas, agrega `time.sleep(1)` entre páginas en `fetch_logs()` |
| `unique constraint violated` o `duplicate key` en HANA | Intentaste insertar registros que ya existen (misma ventana corriendo dos veces, o reintento de CSV parcialmente insertado) | Si tienes PRIMARY KEY: el error es esperado en un retry parcial, puedes ignorarlo. Si no tienes PK: verifica que no haya dos procesos con `ps aux \| grep local_etl` |
| `ModuleNotFoundError: No module named 'hdbcli'` | Dependencias no instaladas | `pip install hdbcli requests pandas python-dotenv` |
| `ModuleNotFoundError: No module named 'dotenv'` | `python-dotenv` no instalado | `pip install python-dotenv` |
| El CSV se crea pero `.inserted` nunca aparece | HANA rechaza todos los inserts (error de esquema, permisos, o tipo de dato) | Lee el error completo en consola. Verifica que las columnas de `INSERT_SYSTEM` e `INSERT_LLM` coincidan con el DDL de tus tablas |
| `logs_backup/` se llena de CSVs sin `.inserted` | HANA está caída durante varios ciclos | El script continúa guardando CSVs localmente. Cuando HANA vuelva, reinicia y los pendientes se insertan en orden |
| Keep-alive imprime `HANA ping FAILED` pero los inserts funcionan | Problema de concurrencia o credenciales en el hilo | Generalmente inofensivo si los ciclos de inserción completan OK. Verifica que `HANA_PASS` en `.env` sea correcta |

---

## 5. Ejemplo de ejecución — primeros 15 minutos

```text
============================================================
  SAP SOC Hackathon — Local ETL Runner
  Iniciado: 2026-04-23 15:00:00
============================================================
[2026-04-23 15:00:00] Probando conexión a HANA...
[2026-04-23 15:00:02] Conexión HANA OK
[2026-04-23 15:00:02] Sin CSVs pendientes de reintentar.
[2026-04-23 15:00:02] [KEEP-ALIVE] Hilo iniciado (cada 300s)
[2026-04-23 15:00:02] Loop principal iniciado (cada 300s).
[2026-04-23 15:00:02] Presiona Ctrl+C para detener.

[2026-04-23 15:00:02] ──── Inicio de ciclo ────
[2026-04-23 15:00:03] API /info → total_pages=4, window_start=2026-04-23T15:00:00Z
[2026-04-23 15:00:03]   Página 1/4: 125 registros
[2026-04-23 15:00:04]   Página 2/4: 125 registros
[2026-04-23 15:00:04]   Página 3/4: 125 registros
[2026-04-23 15:00:05]   Página 4/4: 87 registros
[2026-04-23 15:00:05] Total descargados: 462 logs (window=2026-04-23T15:00:00Z)
[2026-04-23 15:00:05] CSV guardado: logs_backup/2026-04-23T15-00-00Z.csv (462 filas)
[2026-04-23 15:00:06] Insertados 391 system logs
[2026-04-23 15:00:07] Insertados 71 LLM logs
[2026-04-23 15:00:07] HANA commit OK
[2026-04-23 15:00:07] Ciclo completo: 462 filas insertadas.

# ... el proceso duerme 300 segundos ...

[2026-04-23 15:05:02] [KEEP-ALIVE] HANA ping OK

[2026-04-23 15:05:07] ──── Inicio de ciclo ────
[2026-04-23 15:05:08] API /info → total_pages=3, window_start=2026-04-23T15:05:00Z
[2026-04-23 15:05:08]   Página 1/3: 150 registros
[2026-04-23 15:05:09]   Página 2/3: 150 registros
[2026-04-23 15:05:09]   Página 3/3: 134 registros
[2026-04-23 15:05:09] Total descargados: 434 logs (window=2026-04-23T15:05:00Z)
[2026-04-23 15:05:09] CSV guardado: logs_backup/2026-04-23T15-05-00Z.csv (434 filas)
[2026-04-23 15:05:10] Insertados 362 system logs
[2026-04-23 15:05:10] Insertados 72 LLM logs
[2026-04-23 15:05:11] HANA commit OK
[2026-04-23 15:05:11] Ciclo completo: 434 filas insertadas.

# ... el proceso duerme 300 segundos ...

[2026-04-23 15:10:02] [KEEP-ALIVE] HANA ping OK

[2026-04-23 15:10:11] ──── Inicio de ciclo ────
[2026-04-23 15:10:12] API /info → total_pages=4, window_start=2026-04-23T15:10:00Z
[2026-04-23 15:10:12]   Página 1/4: 125 registros
[2026-04-23 15:10:12]   Página 2/4: 125 registros
[2026-04-23 15:10:13]   Página 3/4: 125 registros
[2026-04-23 15:10:13]   Página 4/4: 99 registros
[2026-04-23 15:10:13] Total descargados: 474 logs (window=2026-04-23T15:10:00Z)
[2026-04-23 15:10:13] CSV guardado: logs_backup/2026-04-23T15-10-00Z.csv (474 filas)
[2026-04-23 15:10:14] Insertados 401 system logs
[2026-04-23 15:10:15] Insertados 73 LLM logs
[2026-04-23 15:10:15] HANA commit OK
[2026-04-23 15:10:15] Ciclo completo: 474 filas insertadas.
```

**Estado de `logs_backup/` después de 15 minutos:**

```text
logs_backup/
├── 2026-04-23T15-00-00Z.csv       (462 filas, 87 KB)
├── 2026-04-23T15-00-00Z.inserted  (timestamp de commit)
├── 2026-04-23T15-05-00Z.csv       (434 filas, 82 KB)
├── 2026-04-23T15-05-00Z.inserted
├── 2026-04-23T15-10-00Z.csv       (474 filas, 90 KB)
└── 2026-04-23T15-10-00Z.inserted
```

**Escenario de fallo en el ciclo 2 (HANA caída):**

```text
[2026-04-23 15:05:07] ──── Inicio de ciclo ────
[2026-04-23 15:05:08] API /info → total_pages=3, window_start=2026-04-23T15:05:00Z
...
[2026-04-23 15:05:09] CSV guardado: logs_backup/2026-04-23T15-05-00Z.csv (434 filas)
[2026-04-23 15:05:10] ERROR insertando en HANA: connection refused
[2026-04-23 15:05:10] El respaldo CSV está en: logs_backup/2026-04-23T15-05-00Z.csv
[2026-04-23 15:05:10] Se reintentará automáticamente al próximo reinicio.

# Al reiniciar el script:
[2026-04-23 15:30:00] 1 CSV(s) pendiente(s) — reintentando...
[2026-04-23 15:30:00]   Reintentando: logs_backup/2026-04-23T15-05-00Z.csv
[2026-04-23 15:30:01] Insertados 362 system logs
[2026-04-23 15:30:01] Insertados 72 LLM logs
[2026-04-23 15:30:01] HANA commit OK
[2026-04-23 15:30:01]   OK: logs_backup/2026-04-23T15-05-00Z.csv
```

---

*Script ubicado en: `local_etl.py` — raíz del repositorio*
*Guía ubicada en: `LOCAL_ETL_GUIDE.md`*
