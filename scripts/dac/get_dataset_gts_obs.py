#!/usr/bin/env python

import sys
import argparse
import logging
import datetime
from dateutil import parser
from gdutils import GdacClient
from gdutils.osmc import DuoProfilesClient


def main(args):
    """Fetch all profile times, positions and wmo_id from the IOOS Glider DAC and for the specified dataset id"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    dataset_id = args.dataset_id
    response = args.format

    client = GdacClient()

    # Search for the specified dataset id
    client.search_datasets(dataset_ids=dataset_id)
    if client.datasets.empty:
        logging.warning('No dataset found for dataset_id: {:}'.format(dataset_id))
        return 1

    # Does the dataset have a wmo_id
    if not client.datasets.iloc[0].wmo_id:
        logging.warning('Dataset {:} does not have a WMO id'.format(dataset_id))
        return 1


    osmc_client = DuoProfilesClient()
    osmc_client.dataset_id = args.osmc_dataset_id
    logging.info('Using OSMC dataset: {:}'.format(osmc_client))

    # Fetch observations
    obs = osmc_client.get_profiles_by_wmo_id(client.datasets.iloc[0].wmo_id, client.datasets.iloc[0].start_date,
                                             client.datasets.iloc[0].end_date, gps=args.gps)

    if obs.empty:
        return 1

    if response == 'json':
        sys.stdout.write('{:}\n'.format(obs.reset_index().to_json(orient='records')))
    elif response == 'csv':
        sys.stdout.write('{:}\n'.format(obs.to_csv()))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='ERDDAP glider dataset id',
                            type=str)

    arg_parser.add_argument('--osmc_dataset_id',
                            choices=['OSMCV4_DUO_PROFILES', 'OSMC_30day'],
                            default='OSMCV4_DUO_PROFILES',
                            help='OSMC dataset id to query')

    arg_parser.add_argument('-g', '--gps',
                            help='Include latitude and longtidue in ERDDAP query',
                            action='store_true')

    arg_parser.add_argument('-f', '--format',
                            help='Response format',
                            choices=['json', 'csv'],
                            default='csv')

    arg_parser.add_argument('-x', '--debug',
                            help='Debug mode. No operations performed',
                            action='store_true')

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # sys.stdout.write('{:}'.format(parsed_args))
    # sys.exit(13)

    sys.exit(main(parsed_args))
