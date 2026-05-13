import os
import threading
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from connection import execute_query, get_connection
from system_features import extract_system_features
from llm_features import extract_llm_features

load_dotenv()

MODEL_NAMES = ['IF_SYSTEM_PEAK', 'IF_SYSTEM_OFFPEAK', 'IF_LLM_PEAK', 'IF_LLM_OFFPEAK']


class ScoringEngine:
    def __init__(self):
        self.artifact_dir = Path(__file__).parent / 'artifacts'
        self.models = {}
        self._ready = False
        self._training = False
        self._init()

    def _init(self):
        missing = [n for n in MODEL_NAMES if not (self.artifact_dir / f'{n}.joblib').exists()]
        if missing:
            print(f"Models not found: {missing}. Starting background training...")
            self._training = True
            t = threading.Thread(target=self._train_and_load, daemon=True)
            t.start()
        else:
            self._load_models()

    def _train_and_load(self):
        try:
            from model.train import train_models
            train_models()
            self._load_models()
            print("Background training complete — models ready")
        except Exception as e:
            print(f"Training failed: {e}")
        finally:
            self._training = False

    def _load_models(self):
        for name in MODEL_NAMES:
            path = self.artifact_dir / f'{name}.joblib'
            if path.exists():
                self.models[name] = joblib.load(path)
                print(f"Loaded {name}")
            else:
                print(f"Warning: {name} not found at {path}")
        if len(self.models) == len(MODEL_NAMES):
            self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def training_status(self) -> str:
        if self._ready:
            return "ready"
        if self._training:
            return "training"
        return "error"

    def _get_model_name(self, source_table, hour):
        is_peak = 8 <= hour <= 18
        if source_table == 'SYSTEM':
            return 'IF_SYSTEM_PEAK' if is_peak else 'IF_SYSTEM_OFFPEAK'
        return 'IF_LLM_PEAK' if is_peak else 'IF_LLM_OFFPEAK'

    def score_batch(self, source_table, df):
        if df.empty:
            return pd.DataFrame()

        if source_table == 'SYSTEM':
            features = extract_system_features(df)
        else:
            features = extract_llm_features(df)

        hour = pd.to_datetime(df['TIMESTAMP']).dt.hour.mode()[0]
        model_name = self._get_model_name(source_table, hour)

        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")

        model = self.models[model_name]
        scores_raw = model.score_samples(features)
        predictions = model.predict(features)
        scores_norm = 1 / (1 + np.exp(-scores_raw))

        result_df = df[['ID', 'TIMESTAMP']].copy()
        result_df['SOURCE_TABLE'] = source_table
        result_df['SOURCE_ID'] = df['ID']
        result_df['IS_ANOMALY'] = (predictions == -1).astype(bool)
        result_df['ANOMALY_SCORE'] = scores_norm
        result_df['ANOMALY_TYPE'] = None
        result_df['ML_MODEL_VER'] = 'v1'
        result_df['DETECTED_AT'] = datetime.now(timezone.utc)

        return result_df

    def insert_results(self, results_df):
        if results_df.empty:
            return 0

        rows = [
            (
                row['SOURCE_TABLE'], row['SOURCE_ID'], row['IS_ANOMALY'],
                row['ANOMALY_SCORE'], row['ANOMALY_TYPE'], None,
                row['ML_MODEL_VER'], row['DETECTED_AT']
            )
            for _, row in results_df.iterrows()
        ]

        sql = """
        INSERT INTO ANOMALY_RESULTS
        (SOURCE_TABLE, SOURCE_ID, IS_ANOMALY, ANOMALY_SCORE,
         ANOMALY_TYPE, CLUSTER_ID, ML_MODEL_VER, DETECTED_AT)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(sql, rows)
            conn.commit()
        finally:
            conn.close()
        return len(rows)
