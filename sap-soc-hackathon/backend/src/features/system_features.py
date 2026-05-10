import pandas as pd
from datetime import datetime

def extract_system_features(df):
    """
    Input: df con columnas [TIMESTAMP, LOG_TYPE, HTTP_STATUS_CODE, CLIENT_IP, SERVICE_ID]
    Output: df enriquecido con features para IF
    """
    df = df.copy()
    
    # Temporal features
    df['HOUR'] = pd.to_datetime(df['TIMESTAMP']).dt.hour
    df['IS_PEAK'] = df['HOUR'].between(8, 18).astype(int)
    df['IS_WEEKEND'] = pd.to_datetime(df['TIMESTAMP']).dt.dayofweek >= 5
    
    # Log type encoding
    log_type_map = {'INFO': 0, 'WARNING': 1, 'ERROR': 2, 'SECURITY': 3, 
                    'AUDIT': 4, 'PERF': 5, 'DEBUG': 6}
    df['LOG_TYPE_ENCODED'] = df['LOG_TYPE'].map(log_type_map).fillna(0)
    
    # HTTP status: normalize to 0-1 range
    df['HTTP_STATUS_NORM'] = (df['HTTP_STATUS_CODE'].fillna(200) - 200) / 300
    df['HTTP_STATUS_NORM'] = df['HTTP_STATUS_NORM'].clip(0, 1)
    
    # IP features: ordinal encoding
    df['CLIENT_IP_ENCODED'] = pd.factorize(df['CLIENT_IP'])[0]
    df['CLIENT_IP_ENCODED'] = df['CLIENT_IP_ENCODED'] / df['CLIENT_IP_ENCODED'].max()
    
    # Service features
    df['SERVICE_ID_ENCODED'] = pd.factorize(df['SERVICE_ID'])[0]
    df['SERVICE_ID_ENCODED'] = df['SERVICE_ID_ENCODED'] / df['SERVICE_ID_ENCODED'].max()
    
    # Request count per IP
    df['IP_REQ_COUNT_5M'] = df.groupby('CLIENT_IP').cumcount() + 1
    df['IP_REQ_COUNT_5M'] = df['IP_REQ_COUNT_5M'] / df['IP_REQ_COUNT_5M'].max()
    
    # Error ratio por IP
    df['IP_ERROR_RATIO'] = (df['HTTP_STATUS_CODE'] >= 400).astype(int)
    
    return df[['LOG_TYPE_ENCODED', 'HTTP_STATUS_NORM', 'CLIENT_IP_ENCODED', 
               'SERVICE_ID_ENCODED', 'IS_PEAK', 'IS_WEEKEND', 'HOUR', 
               'IP_REQ_COUNT_5M', 'IP_ERROR_RATIO']]