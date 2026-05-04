import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
from pathlib import Path
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.system_features import extract_system_features
from features.llm_features import extract_llm_features

def train_isolation_forest(features_df, model_name, contamination=0.02, n_estimators=100):
    """
    features_df: pandas DataFrame con features
    model_name: 'IF_SYSTEM_PEAK', etc.
    """
    print(f"Training {model_name}...")
    
    features_df = features_df.dropna()
    
    if len(features_df) < 100:
        raise ValueError(f"Not enough training data: {len(features_df)} rows")
    
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=42,
        n_jobs=-1
    )
    
    predictions = model.fit_predict(features_df)
    scores = model.score_samples(features_df)
    
    # Guardar modelo
    artifact_path = Path(__file__).parent.parent.parent / 'artifacts' / f'{model_name}.joblib'
    joblib.dump(model, artifact_path)
    print(f"✓ Model saved to {artifact_path}")
    
    # Stats
    print(f"  Training records: {len(features_df)}")
    print(f"  Anomalies detected: {(predictions == -1).sum()}")
    print(f"  Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    print(f"  Score P5: {np.percentile(scores, 5):.3f}")
    print(f"  Score P95: {np.percentile(scores, 95):.3f}")
    
    return {
        'model': model,
        'scores': scores,
        'predictions': predictions,
        'stats': {
            'training_rows': len(features_df),
            'contamination': contamination,
            'n_estimators': n_estimators,
            'score_mean': float(scores.mean()),
            'score_p5': float(np.percentile(scores, 5)),
            'score_p95': float(np.percentile(scores, 95)),
            'anomaly_count': int((predictions == -1).sum())
        }
    }

def load_and_train_all():
    """
    Carga CSVs reales de backend/data/ y entrena los 4 modelos
    """
    data_dir = Path(__file__).parent.parent.parent / 'data'
    
    # Carga CSV de system logs (peak)
    system_peak_path = data_dir / 'system_logs_peak.csv'
    if not system_peak_path.exists():
        raise FileNotFoundError(f"Missing: {system_peak_path}")
    
    system_peak_df = pd.read_csv(system_peak_path)
    system_peak_features = extract_system_features(system_peak_df)
    train_isolation_forest(system_peak_features, 'IF_SYSTEM_PEAK', contamination=0.02)
    
    print()
    
    # System offpeak
    system_offpeak_path = data_dir / 'system_logs_offpeak.csv'
    if not system_offpeak_path.exists():
        raise FileNotFoundError(f"Missing: {system_offpeak_path}")
    
    system_offpeak_df = pd.read_csv(system_offpeak_path)
    system_offpeak_features = extract_system_features(system_offpeak_df)
    train_isolation_forest(system_offpeak_features, 'IF_SYSTEM_OFFPEAK', contamination=0.04)
    
    print()
    
    # LLM peak
    llm_peak_path = data_dir / 'llm_logs_peak.csv'
    if not llm_peak_path.exists():
        raise FileNotFoundError(f"Missing: {llm_peak_path}")
    
    llm_peak_df = pd.read_csv(llm_peak_path)
    llm_peak_features = extract_llm_features(llm_peak_df)
    train_isolation_forest(llm_peak_features, 'IF_LLM_PEAK', contamination=0.02)
    
    print()
    
    # LLM offpeak
    llm_offpeak_path = data_dir / 'llm_logs_offpeak.csv'
    if not llm_offpeak_path.exists():
        raise FileNotFoundError(f"Missing: {llm_offpeak_path}")
    
    llm_offpeak_df = pd.read_csv(llm_offpeak_path)
    llm_offpeak_features = extract_llm_features(llm_offpeak_df)
    train_isolation_forest(llm_offpeak_features, 'IF_LLM_OFFPEAK', contamination=0.04)
    
    print("\n✓ All 4 models trained and saved")

if __name__ == '__main__':
    print("=== Training Local Fallback Models ===\n")
    load_and_train_all()