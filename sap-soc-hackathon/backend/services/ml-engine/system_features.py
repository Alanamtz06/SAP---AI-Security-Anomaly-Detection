import pandas as pd


def extract_system_features(df):
    df = df.copy()

    df['HOUR'] = pd.to_datetime(df['TIMESTAMP']).dt.hour
    df['IS_PEAK'] = df['HOUR'].between(8, 18).astype(int)
    df['IS_WEEKEND'] = pd.to_datetime(df['TIMESTAMP']).dt.dayofweek >= 5

    log_type_map = {'INFO': 0, 'WARNING': 1, 'ERROR': 2, 'SECURITY': 3,
                    'AUDIT': 4, 'PERF': 5, 'DEBUG': 6}
    df['LOG_TYPE_ENCODED'] = df['LOG_TYPE'].map(log_type_map).fillna(0)

    df['HTTP_STATUS_NORM'] = (df['HTTP_STATUS_CODE'].fillna(200) - 200) / 300
    df['HTTP_STATUS_NORM'] = df['HTTP_STATUS_NORM'].clip(0, 1)

    df['CLIENT_IP_ENCODED'] = pd.factorize(df['CLIENT_IP'])[0]
    df['CLIENT_IP_ENCODED'] = df['CLIENT_IP_ENCODED'] / df['CLIENT_IP_ENCODED'].max()

    df['SERVICE_ID_ENCODED'] = pd.factorize(df['SERVICE_ID'])[0]
    df['SERVICE_ID_ENCODED'] = df['SERVICE_ID_ENCODED'] / df['SERVICE_ID_ENCODED'].max()

    df['IP_REQ_COUNT_5M'] = df.groupby('CLIENT_IP').cumcount() + 1
    df['IP_REQ_COUNT_5M'] = df['IP_REQ_COUNT_5M'] / df['IP_REQ_COUNT_5M'].max()

    df['IP_ERROR_RATIO'] = (df['HTTP_STATUS_CODE'] >= 400).astype(int)

    return df[['LOG_TYPE_ENCODED', 'HTTP_STATUS_NORM', 'CLIENT_IP_ENCODED',
               'SERVICE_ID_ENCODED', 'IS_PEAK', 'IS_WEEKEND', 'HOUR',
               'IP_REQ_COUNT_5M', 'IP_ERROR_RATIO']]
