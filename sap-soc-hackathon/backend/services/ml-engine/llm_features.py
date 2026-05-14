import pandas as pd
import numpy as np


def extract_llm_features(df):
    df = df.copy()

    df['HOUR'] = pd.to_datetime(df['TIMESTAMP']).dt.hour
    df['IS_PEAK'] = df['HOUR'].between(8, 18).astype(int)
    df['IS_WEEKEND'] = pd.to_datetime(df['TIMESTAMP']).dt.dayofweek >= 5

    log_type_map = {'LLM_REQUEST': 0, 'LLM_ERROR': 1, 'LLM_TIMEOUT': 2}
    df['LOG_TYPE_ENCODED'] = df['LOG_TYPE'].map(log_type_map).fillna(0)

    status_map = {'SUCCESS': 0, 'success': 0, 'ERROR': 1, 'error': 1, 'TIMEOUT': 2, 'timeout': 2}
    df['LLM_STATUS_ENCODED'] = df['LLM_STATUS'].map(status_map).fillna(0)

    df['LLM_COST_LOG'] = np.log1p(df['LLM_COST_USD'].fillna(0))
    max_cost_log = np.log1p(0.137)
    df['LLM_COST_NORM'] = df['LLM_COST_LOG'] / max_cost_log
    df['LLM_COST_NORM'] = df['LLM_COST_NORM'].clip(0, 1)

    df['LLM_RESPONSE_TIME_NORM'] = (df['LLM_RESPONSE_TIME_MS'].fillna(2000) - 200) / (34999 - 200)
    df['LLM_RESPONSE_TIME_NORM'] = df['LLM_RESPONSE_TIME_NORM'].clip(0, 1)

    df['LLM_MODEL_ENCODED'] = pd.factorize(df['LLM_MODEL_ID'])[0]
    df['LLM_MODEL_ENCODED'] = (df['LLM_MODEL_ENCODED'] / df['LLM_MODEL_ENCODED'].max()).fillna(0)

    df['MODEL_REQ_COUNT'] = df.groupby('LLM_MODEL_ID').cumcount() + 1
    df['MODEL_REQ_COUNT'] = (df['MODEL_REQ_COUNT'] / df['MODEL_REQ_COUNT'].max()).fillna(0)

    df['MODEL_ERROR_RATE'] = (df['LLM_STATUS_ENCODED'] > 0).astype(int)

    return df[['LOG_TYPE_ENCODED', 'LLM_STATUS_ENCODED', 'LLM_COST_NORM',
               'LLM_RESPONSE_TIME_NORM', 'LLM_MODEL_ENCODED', 'IS_PEAK', 'IS_WEEKEND',
               'HOUR', 'MODEL_REQ_COUNT', 'MODEL_ERROR_RATE']]
