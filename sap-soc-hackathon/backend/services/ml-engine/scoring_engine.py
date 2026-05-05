import os
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Agregar paths
sys.path.insert(0, os.path.abspath('../../src'))
from db.connection import execute_query, get_connection
from features.system_features import extract_system_features
from features.llm_features import extract_llm_features

load_dotenv()

class ScoringEngine:
    def __init__(self):
        self.artifact_dir = Path(__file__).parent.parent.parent / 'artifacts'
        self.models = self._load_models()

    def _load_models(self):
        """Carga los 4 modelos desde artifacts/"""
        models = {}
        model_names = [
            'IF_SYSTEM_PEAK', 'IF_SYSTEM_OFFPEAK',
            'IF_LLM_PEAK', 'IF_LLM_OFFPEAK'
        ]
        for name in model_names:
            path = self.artifact_dir / f'{name}.joblib'
            if path.exists():
                models[name] = joblib.load(path)
                print(f"✓ Loaded {name}")
            else:
                print(f"⚠ {name} not found")
        return models

    def _get_model_name(self, source_table, hour):
        """Selecciona modelo según tabla y hora"""
        is_peak = 8 <= hour <= 18
        is_weekday = True  # TODO: verificar día

        if source_table == 'SYSTEM':
            return 'IF_SYSTEM_PEAK' if is_peak else 'IF_SYSTEM_OFFPEAK'
        else:  # LLM
            return 'IF_LLM_PEAK' if is_peak else 'IF_LLM_OFFPEAK'

    def score_batch(self, source_table, df):
        """
        Puntúa un batch de logs
        source_table: 'SYSTEM' o 'LLM'
        df: DataFrame con logs
        Returns: DataFrame con scores
        """
        if df.empty:
            return pd.DataFrame()

        # Extraer features
        if source_table == 'SYSTEM':
            features = extract_system_features(df)
        else:
            features = extract_llm_features(df)

        # Seleccionar modelo (usar hora promedio del batch)
        hour = pd.to_datetime(df['TIMESTAMP']).dt.hour.mode()[0]
        model_name = self._get_model_name(source_table, hour)

        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")

        model = self.models[model_name]

        # Scoring
        scores_raw = model.score_samples(features)
        predictions = model.predict(features)

        # Normalizar scores (sklearn: -1=outlier, +1=inlier)
        # Convertir a [0, 1] donde 1 = más anómalo
        scores_norm = 1 / (1 + np.exp(-scores_raw))

        # Crear resultado
        result_df = df[['ID', 'TIMESTAMP']].copy()
        result_df['SOURCE_TABLE'] = source_table
        result_df['SOURCE_ID'] = df['ID']
        result_df['IS_ANOMALY'] = (predictions == -1).astype(bool)
        result_df['ANOMALY_SCORE'] = scores_norm
        result_df['ANOMALY_TYPE'] = None
        result_df['ML_MODEL_VER'] = 'v1'
        result_df['DETECTED_AT'] = datetime.utcnow()

        return result_df

    def insert_results(self, results_df):
        """Inserta resultados en ANOMALY_RESULTS"""
        if results_df.empty:
            return 0

        # Preparar para INSERT
        rows = []
        for _, row in results_df.iterrows():
            rows.append((
                row['SOURCE_TABLE'],
                row['SOURCE_ID'],
                row['IS_ANOMALY'],
                row['ANOMALY_SCORE'],
                row['ANOMALY_TYPE'],
                None,  # CLUSTER_ID
                row['ML_MODEL_VER'],
                row['DETECTED_AT']
            ))

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
