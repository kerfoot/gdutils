import requests
import logging
import pandas as pd

dac_catalog_url = 'https://gliders.ioos.us/providers/api/deployment'

logging.getLogger(__file__)


def fetch_dac_catalog_dataframe(url=None):
    """
    Fetch the DAC deployments API json response and convert to a DataFrame with appropriate data types.
    :param url: Alternate url end point
    :return: pandas DataFrame
    """

    catalog = fetch_dac_catalog_json(url=url)
    if not catalog:
        return pd.DataFrame()

    df = pd.DataFrame(catalog).rename(columns={'name': 'dataset_id'}).set_index('dataset_id')

    drop_cols = ['estimated_deploy_date',
                 'estimated_deploy_location']

    df.drop(columns=drop_cols, inplace=True)

    boolean_cols = ['archive_safe',
                    'completed',
                    'compliance_check_passed',
                    'delayed_mode']

    # Convert boolean_cols to boolean dtype
    for col in boolean_cols:
        df[col] = df[col].astype('bool')

    timestamp_cols = ['created',
                      'deployment_date',
                      'latest_file_mtime',
                      'updated']

    # Convert timestamp_cols to datetime64[ns] dtype
    for col in timestamp_cols:
        df[col] = pd.to_datetime(df[col]/1000, utc=True, format='s', errors='coerce')

    return df


def fetch_dac_catalog_json(url=None):
    """
    Fetch the API end point response located at gdutils.apis.dac.dac_catalog_url
    :param url: Alternate url end point
    :return: json
    """

    url = url or dac_catalog_url

    logging.info('Fetching API registered data sets from {:}'.format(url))

    try:
        r = requests.get(dac_catalog_url, timeout=60)
    except requests.exceptions.ReadTimeout as e:
        logging.error('Failed to fetch API endpoint {:} ({:})'.format(url, e))
        return []

    if r.status_code == 200:
        return r.json()['results']

    logging.error('Failed to fetch DAC registered deployments: {:}'.format(r.reason))

    return []
