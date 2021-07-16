#!/usr/bin/env python

import sys
import argparse
import logging
import datetime
from dateutil import parser
from gdutils import GdacClient


def main(args):
    """Fetch all profile times, positions and wmo_id from the IOOS Glider DAC and for the specified dataset id"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    dataset_id = args.dataset_id
    response = args.format

    client = GdacClient()

    profiles = client.get_dataset_profiles(dataset_id)
    if profiles.empty:
        return 1

    if response == 'json':
        sys.stdout.write('{:}\n'.format(profiles.reset_index().to_json(orient='records')))
    elif response == 'csv':
        sys.stdout.write('{:}\n'.format(profiles.to_csv()))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='ERDDAP glider dataset id',
                            type=str)

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

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))