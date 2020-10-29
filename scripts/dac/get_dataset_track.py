#!/usr/bin/env python

import argparse
import logging
import sys
import json
import pandas as pd
from gdutils import GdacClient
# from gdutils.dac import fetch_dac_catalog


def main(args):
    """Fetch and print the geoJSON track for the specified dataset_id from the IOOS Glider DAC"""

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    dataset_id = args.dataset_id
    response = args.format

    # Fire up the GdacClient
    client = GdacClient()

    client.search_datasets(dataset_ids=dataset_id)
    if client.datasets.empty:
        logging.warning('Dataset not found: {:}'.format(dataset_id))
        return 1

    if response == 'json':
        track = client.get_dataset_track_geojson(dataset_id)
        sys.stdout.write('{:}\n'.format(json.dumps(track)))
    elif response == 'csv':
        track = client.get_dataset_profiles(dataset_id)
        sys.stdout.write('{:}\n'.format(track.to_csv()))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='ERDDAP dataset id')

    arg_parser.add_argument('-f', '--format',
                            help='Response format',
                            choices=['json', 'csv'],
                            default='json')

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))