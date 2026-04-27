import logging
import sys
import time
from typing import Any, Optional

from connection import get_connection
from deduplicator import should_create_incident
from message_builder import build_alert_message
from severity_mapper import derive_severity, map_attack_type
from webhook import send_alert

CYCLE_INTERVAL           = 30   # seconds
MAX_ANOMALIES_PER_CYCLE  = 100

_TABLE_MAP = {"SYSTEM": "SAP_SYSTEM_LOGS", "LLM": "SAP_LLM_LOGS"}

log = logging.getLogger("soc.alerter")


class AlertingService:
    def __init__(self) -> None:
        self.running  = False
        self.conn: Any = None
        self._cycles        = 0
        self._alerts_sent   = 0
        self._alerts_failed = 0

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        log.info("Conectando a HANA...")
        try:
            self.conn = get_connection()
            cur = self.conn.cursor()
            cur.execute("SELECT 1 FROM DUMMY")
            cur.close()
            log.info("Conexión HANA establecida")
            return True
        except Exception as exc:
            log.error(f"[db] HANA connection FAILED: {exc}", exc_info=True)
            return False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        if not self.connect():
            sys.exit(1)
        self.running = True
        log.info("Iniciando loop principal")
        while self.running:
            try:
                self.cycle()
            except Exception as exc:
                log.error(f"cycle error: {exc}", exc_info=True)
            time.sleep(CYCLE_INTERVAL)

    # ── Cycle ─────────────────────────────────────────────────────────────────

    def cycle(self) -> None:
        start = time.monotonic()
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT ar.ID, ar.SOURCE_TABLE, ar.SOURCE_ID,
                   ar.ANOMALY_SCORE, ar.ANOMALY_TYPE, ar.DETECTED_AT
            FROM   ANOMALY_RESULTS ar
            LEFT JOIN INCIDENTS i ON i.ANOMALY_ID = ar.ID
            WHERE  ar.IS_ANOMALY = TRUE
              AND  i.ID IS NULL
            ORDER BY ar.DETECTED_AT ASC
            LIMIT {MAX_ANOMALIES_PER_CYCLE}
            """
        )
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        cur.close()

        sent = skipped = errors = 0
        for row in rows:
            try:
                if self.process_anomaly(dict(zip(cols, row))):
                    sent += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
                log.error(f"process_anomaly error: {exc}", exc_info=True)

        self._cycles += 1
        if rows:
            elapsed = time.monotonic() - start
            log.info(
                f"cycle #{self._cycles} done in {elapsed:.1f}s — "
                f"{sent} alerted, {skipped} skipped/deduped, {errors} errors"
            )
        else:
            log.debug("Sin anomalías nuevas")

    # ── Per-anomaly logic ─────────────────────────────────────────────────────

    def process_anomaly(self, anomaly: dict[str, Any]) -> bool:
        anomaly_id:   int = anomaly["ID"]
        source_table: str = str(anomaly.get("SOURCE_TABLE") or "")
        source_id:    int = int(anomaly.get("SOURCE_ID") or 0)
        anomaly_type: str = str(anomaly.get("ANOMALY_TYPE") or "")
        score = anomaly.get("ANOMALY_SCORE")

        severity     = derive_severity(score, anomaly_type or None)
        attack_label = map_attack_type(anomaly_type or None)

        should_create, existing_id = should_create_incident(
            self.conn, anomaly_type, source_table, source_id
        )

        if not should_create and existing_id is not None:
            self._create_dedup_marker(anomaly_id, severity, attack_label)
            self.update_occurrence_count(existing_id)
            log.info(f"DEDUP anomaly={anomaly_id} → INCIDENT #{existing_id}")
            return False

        source_log = self.get_source_log(source_table, source_id)
        message    = build_alert_message(source_table, score, anomaly_type, severity, source_log)

        incident_id = self.create_incident(anomaly_id, severity, attack_label)
        if incident_id is None:
            log.error(f"failed to create incident for anomaly={anomaly_id}")
            return False

        log.info(f"INCIDENT #{incident_id} | {severity} | {attack_label} | anomaly={anomaly_id}")

        webhook_status = send_alert(
            message, severity,
            anomaly_id=anomaly_id,
            incident_id=incident_id,
            attack_type=attack_label,
        )
        alert_sent = webhook_status == "SUCCESS"
        self.update_incident_status(incident_id, alert_sent, webhook_status)

        if alert_sent:
            self._alerts_sent += 1
            log.info(f"INCIDENT #{incident_id} SUCCESS")
        else:
            self._alerts_failed += 1
            log.warning(f"INCIDENT #{incident_id} FAILED")

        return alert_sent

    # ── DB helpers ────────────────────────────────────────────────────────────

    def get_source_log(self, source_table: str, source_id: int) -> Optional[tuple]:
        table = _TABLE_MAP.get(source_table)
        if not table:
            return None
        try:
            cur = self.conn.cursor()
            cur.execute(f"SELECT * FROM {table} WHERE ID = ?", (source_id,))
            row = cur.fetchone()
            cur.close()
            return row
        except Exception as exc:
            log.warning(f"[ctx] {source_table}#{source_id}: {exc}")
            return None

    def create_incident(
        self, anomaly_id: int, severity: str, attack_type: str
    ) -> Optional[int]:
        try:
            cur = self.conn.cursor()
            cur.execute(
                """INSERT INTO INCIDENTS
                       (ANOMALY_ID, SEVERITY, ATTACK_TYPE, WEBHOOK_STATUS, OCCURRENCE_COUNT)
                   VALUES (?, ?, ?, 'PENDING', 1)""",
                (anomaly_id, severity, attack_type),
            )
            cur.execute("SELECT CURRENT_IDENTITY_VALUE() FROM DUMMY")
            incident_id: int = cur.fetchone()[0]
            self.conn.commit()
            cur.close()
            return incident_id
        except Exception as exc:
            log.error(f"create_incident failed: {exc}", exc_info=True)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return None

    def _create_dedup_marker(
        self, anomaly_id: int, severity: str, attack_type: str
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO INCIDENTS
                   (ANOMALY_ID, SEVERITY, ATTACK_TYPE,
                    WEBHOOK_STATUS, ALERT_SENT, RESOLVED, OCCURRENCE_COUNT)
               VALUES (?, ?, ?, 'DEDUP', FALSE, TRUE, 0)""",
            (anomaly_id, severity, attack_type),
        )
        self.conn.commit()
        cur.close()

    def update_incident_status(
        self, incident_id: int, alert_sent: bool, webhook_status: str
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE INCIDENTS
               SET ALERT_SENT = ?, WEBHOOK_STATUS = ?, UPDATED_AT = CURRENT_TIMESTAMP
               WHERE ID = ?""",
            (alert_sent, webhook_status, incident_id),
        )
        self.conn.commit()
        cur.close()

    def update_occurrence_count(self, incident_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE INCIDENTS
               SET OCCURRENCE_COUNT = OCCURRENCE_COUNT + 1,
                   UPDATED_AT = CURRENT_TIMESTAMP
               WHERE ID = ?""",
            (incident_id,),
        )
        self.conn.commit()
        cur.close()

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def stop(self) -> None:
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        log.info(
            f"SOC Alerting Service stopped — "
            f"{self._cycles} cycles, {self._alerts_sent} sent, "
            f"{self._alerts_failed} failed"
        )
