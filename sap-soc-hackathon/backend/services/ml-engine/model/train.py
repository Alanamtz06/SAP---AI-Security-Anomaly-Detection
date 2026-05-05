import sys
import numpy as np
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).parent.parent))

from connection import execute_query
from system_features import extract_system_features
from llm_features import extract_llm_features

ARTIFACT_DIR = Path(__file__).parent.parent / 'artifacts'


def _train_one(features_df: pd.DataFrame, model_name: str, contamination: float) -> IsolationForest:
    features_df = features_df.dropna()
    if len(features_df) < 100:
        raise ValueError(f"Not enough data for {model_name}: {len(features_df)} rows")

    print(f"Training {model_name} on {len(features_df)} records...")
    model = IsolationForest(
        contamination=contamination,
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )
    model.fit(features_df)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACT_DIR / f'{model_name}.joblib'
    joblib.dump(model, out_path)
    print(f"✓ Saved {model_name} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return model


def train_models():
    """Query HANA, extract features, train 4 IsolationForest models, save to artifacts/."""
    print("=== Starting model training ===")

    print("Fetching System PEAK logs...")
    sys_peak = execute_query("""
        SELECT TIMESTAMP, LOG_TYPE, HTTP_STATUS_CODE, CLIENT_IP, SERVICE_ID
        FROM SAP_SYSTEM_LOGS
        WHERE EXTRACT(HOUR FROM TIMESTAMP) BETWEEN 8 AND 18
            AND DAYOFWEEK(TIMESTAMP) BETWEEN 2 AND 6
        LIMIT 100000
    """)

    print("Fetching System OFFPEAK logs...")
    sys_offpeak = execute_query("""
        SELECT TIMESTAMP, LOG_TYPE, HTTP_STATUS_CODE, CLIENT_IP, SERVICE_ID
        FROM SAP_SYSTEM_LOGS
        WHERE (EXTRACT(HOUR FROM TIMESTAMP) < 8 OR EXTRACT(HOUR FROM TIMESTAMP) > 18)
            OR DAYOFWEEK(TIMESTAMP) NOT BETWEEN 2 AND 6
        LIMIT 100000
    """)

    print("Fetching LLM PEAK logs...")
    llm_peak = execute_query("""
        SELECT TIMESTAMP, LOG_TYPE, LLM_MODEL_ID, LLM_STATUS, LLM_COST_USD, LLM_RESPONSE_TIME_MS
        FROM SAP_LLM_LOGS
        WHERE EXTRACT(HOUR FROM TIMESTAMP) BETWEEN 8 AND 18
            AND DAYOFWEEK(TIMESTAMP) BETWEEN 2 AND 6
        LIMIT 100000
    """)

    print("Fetching LLM OFFPEAK logs...")
    llm_offpeak = execute_query("""
        SELECT TIMESTAMP, LOG_TYPE, LLM_MODEL_ID, LLM_STATUS, LLM_COST_USD, LLM_RESPONSE_TIME_MS
        FROM SAP_LLM_LOGS
        WHERE (EXTRACT(HOUR FROM TIMESTAMP) < 8 OR EXTRACT(HOUR FROM TIMESTAMP) > 18)
            OR DAYOFWEEK(TIMESTAMP) NOT BETWEEN 2 AND 6
        LIMIT 100000
    """)

    _train_one(extract_system_features(pd.DataFrame(sys_peak)),    'IF_SYSTEM_PEAK',    0.02)
    _train_one(extract_system_features(pd.DataFrame(sys_offpeak)), 'IF_SYSTEM_OFFPEAK', 0.04)
    _train_one(extract_llm_features(pd.DataFrame(llm_peak)),       'IF_LLM_PEAK',       0.02)
    _train_one(extract_llm_features(pd.DataFrame(llm_offpeak)),    'IF_LLM_OFFPEAK',    0.04)

    print("=== Training complete — 4 models saved ===")


if __name__ == '__main__':
    train_models()
