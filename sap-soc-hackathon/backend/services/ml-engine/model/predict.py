import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ARTIFACT_DIR = Path(__file__).parent.parent / "artifacts"

def load_model(model_name: str):
    """Load a trained IsolationForest model from artifacts/"""
    path = ARTIFACT_DIR / f"{model_name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    return joblib.load(path)

def get_model_name(source_table: str, hour: int) -> str:
    """Select model based on source table and hour of day"""
    is_peak = 8 <= hour <= 18
    if source_table == "SYSTEM":
        return "IF_SYSTEM_PEAK" if is_peak else "IF_SYSTEM_OFFPEAK"
    else:
        return "IF_LLM_PEAK" if is_peak else "IF_LLM_OFFPEAK"

def predict(features: np.ndarray, model_name: str) -> dict:
    """
    Run prediction on feature array.
    Returns dict with raw scores, normalized scores, and predictions.
    """
    model = load_model(model_name)

    scores_raw = model.score_samples(features)
    predictions = model.predict(features)

    # Normalize scores to [0, 1] where 1 = most anomalous
    scores_norm = 1 / (1 + np.exp(-scores_raw))

    return {
        "predictions": predictions.tolist(),       # -1=anomaly, 1=normal
        "scores_raw": scores_raw.tolist(),
        "scores_norm": scores_norm.tolist(),
        "is_anomaly": (predictions == -1).tolist(),
        "model_name": model_name
    }

def predict_single(feature_dict: dict, source_table: str, hour: int) -> dict:
    """
    Predict for a single log record.
    feature_dict: dict of feature name -> value
    source_table: 'SYSTEM' or 'LLM'
    hour: hour of day (0-23)
    """
    model_name = get_model_name(source_table, hour)
    features = np.array(list(feature_dict.values())).reshape(1, -1)
    return predict(features, model_name)
