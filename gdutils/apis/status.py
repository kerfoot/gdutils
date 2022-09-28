import requests
import logging
import pandas as pd

datasets_status_url = 'http://localhost/dac/status-dev/api/index.php?cat=datasets'

logging.getLogger(__file__)


def fetch_datasets_status_dataframe(url=None):

    response = fetch_datasets_status_json(url=url)

    df = pd.DataFrame(response).set_index('dataset_id')

    boolean_cols = ['archive_safe',
                    'completed',
                    'compliance_check_passed',
                    'delayed_mode']

    # Convert boolean_cols to boolean dtype
    for col in boolean_cols:
        df[col] = df[col].astype('int').astype('bool')

    int_cols = ['num_profiles',
                'days']

    # Convert int_cols to int dtype
    for col in int_cols:
        df[col] = df[col].fillna('0').astype('int')

    timestamp_cols = ['created',
                      'latest_file_mtime',
                      'start_date',
                      'end_date']

    # Convert timestamp_cols to datetime64[ns] dtype
    for col in timestamp_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    float_cols = ['deployment_lat',
                  'deployment_lon',
                  'lat_min',
                  'lat_max',
                  'lon_min',
                  'lon_max']

    # Convert float_cols to float dtype
    for col in float_cols:
        df[col] = df[col].astype('float')

    # Create a new column ('orphaned') set to True where there is no ERDDAP tabledap end point
    df['orphaned'] = True
    df['orphaned'].where(df['tabledap'].isnull(), False, inplace=True)

    return df


def fetch_datasets_status_json(url=None):

    url = url or datasets_status_url

    try:
        r = requests.get(url)
        if r.status_code != 200:
            logging.error(r.reason)
            return []

        return r.json()['records']

    except Exception as e:
        logging.error(e)
        return []

