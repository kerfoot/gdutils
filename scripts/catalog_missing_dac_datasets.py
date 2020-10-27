#!/usr/bin/env python

import argparse
import logging
import os
import sys
import json
import datetime
from gdutils import GdacClient
from gdutils.dac import fetch_dac_catalog, latlon_to_geojson_track
from decimal import *
from operator import itemgetter


def main(args):
    """Create catalogs for all real-time glider datasets located at the IOOS Glider Data Assembly Center"""

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    if not os.path.isdir(args.outputdir):
        logging.error('Invalid destination path: {:}'.format(args.output_dir))
        return 1

    datasets_path = os.path.join(args.outputdir, 'datasets')
    if not os.path.isdir(datasets_path):
        logging.info('Creating datasets path: {:}'.format(datasets_path))
        try:
            os.mkdir(datasets_path)
        except OSError as e:
            logging.error('Error creating {:}: {:}'.format(datasets_path, e))
            return 1

    # Fetch the DAC registered deployments
    datasets = fetch_dac_catalog()
    if not datasets:
        return 1

    # Fire up the GdacClient
    client = GdacClient()

    missing_catalog = []
    for dataset in datasets:

        dataset_id = dataset['name']

        # check to see if the dataset is on the ERDDAP server
        exists = client.check_dataset_exists(dataset_id)
        if exists:
            continue

        # Create created_ts and updated_ts from unix ms times
        dataset['created_ts'] = datetime.datetime.utcfromtimestamp(dataset['created']/1000)
        dataset['updated_ts'] = datetime.datetime.utcfromtimestamp(dataset['updated']/1000)
        dataset['deployment_date_ts'] = datetime.datetime.utcfromtimestamp(dataset['deployment_date']/1000)

        missing_catalog.append(dataset)

    status_path = os.path.join(args.outputdir, 'missing.json')
    try:
        with open(status_path, 'w') as fid:
            json.dump(sorted(missing_catalog, key=itemgetter('created_ts'), reverse=True), fid, default=str, sort_keys=True)
    except IOError as e:
        logging.error('Error writing status file: {:}'.format(status_path))
        return 1

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # arg_parser.add_argument('-s', '--status',
    #                         help='Process all deployments regardless of completed status',
    #                         choices=['active', 'completed', 'all'],
    #                         default='active')
    #
    # arg_parser.add_argument('-d', '--delayed',
    #                         help='Process delayed mode datasets also',
    #                         action='store_true')

    arg_parser.add_argument('-o', '--outputdir',
                            help='Location to write individual sensor definition json files',
                            default=os.path.realpath(os.curdir))

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))