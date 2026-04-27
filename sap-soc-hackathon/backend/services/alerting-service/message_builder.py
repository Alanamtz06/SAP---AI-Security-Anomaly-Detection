from typing import Optional

from severity_mapper import ATTACK_TYPE_MAP

# Column indices for SAP_SYSTEM_LOGS (SELECT *)
_SYS_LOG_TYPE     = 2
_SYS_HTTP_STATUS  = 3
_SYS_CLIENT_IP    = 4
_SYS_SERVICE_ID   = 5

# Column indices for SAP_LLM_LOGS (SELECT *)
_LLM_MODEL_ID     = 3
_LLM_COST_USD     = 5


def build_alert_message(
    source_table: str,
    score: Optional[float],
    anom_type: Optional[str],
    severity: str,
    source_log: Optional[tuple],
) -> str:
    """Build compact alert message ≤300 chars, enriched with source context."""
    key = (anom_type or "").lower().strip()
    attack_label = ATTACK_TYPE_MAP.get(key, (anom_type or "Unknown").replace("_", " ").title())
    score_str = f"{score:.2f}" if score is not None else "?"

    if source_table == "SYSTEM" and source_log:
        client_ip  = source_log[_SYS_CLIENT_IP]  if len(source_log) > _SYS_CLIENT_IP  else "?"
        service_id = source_log[_SYS_SERVICE_ID] if len(source_log) > _SYS_SERVICE_ID else "?"
        http_st    = source_log[_SYS_HTTP_STATUS] if len(source_log) > _SYS_HTTP_STATUS else "?"
        msg = (
            f"[{severity}] {attack_label} from {client_ip} to SVC:{service_id}"
            f" | HTTP:{http_st} | Score:{score_str}"
        )
    elif source_table == "LLM" and source_log:
        model = source_log[_LLM_MODEL_ID] if len(source_log) > _LLM_MODEL_ID else "?"
        cost  = source_log[_LLM_COST_USD] if len(source_log) > _LLM_COST_USD else None
        model_str = str(model)[:30] if model else "?"
        cost_str  = f"${float(cost):.4f}" if cost is not None else "?"
        msg = (
            f"[{severity}] {attack_label} on {model_str}"
            f" | Score:{score_str} | Cost:{cost_str}"
        )
    else:
        msg = f"[{severity}] {attack_label} | Score:{score_str}"

    if len(msg) > 300:
        return msg[:297] + "..."
    return msg
