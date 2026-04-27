from typing import Optional

ATTACK_TYPE_MAP: dict[str, str] = {
    "brute_force":      "Brute Force Attack",
    "spike":            "Traffic Spike",
    "scan":             "Network Scan",
    "injection":        "Injection Attack",
    "llm_abuse":        "LLM Abuse",
    "lateral_movement": "Lateral Movement",
    "novelty":          "Novel Service",
    "borderline":       "Suspicious Behavior",
}

_SEVERITY_BY_TYPE: dict[str, str] = {
    "brute_force":      "CRITICAL",
    "injection":        "CRITICAL",
    "lateral_movement": "CRITICAL",
    "scan":             "HIGH",
    "spike":            "HIGH",
    "llm_abuse":        "HIGH",
    "novelty":          "MEDIUM",
    "borderline":       "MEDIUM",
}


def derive_severity(score: Optional[float], anom_type: Optional[str]) -> str:
    if anom_type:
        sev = _SEVERITY_BY_TYPE.get(anom_type.lower().strip())
        if sev:
            return sev
    if score is None:
        return "MEDIUM"
    if score >= 0.9:
        return "CRITICAL"
    if score >= 0.7:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


def map_attack_type(anom_type: Optional[str]) -> str:
    if not anom_type:
        return "Unknown Threat"
    key = anom_type.lower().strip()
    return ATTACK_TYPE_MAP.get(key, anom_type.replace("_", " ").title())
