#!/usr/bin/env python

import sys
import argparse
import logging
import datetime
from dateutil import parser
from gdutils import GdacClient


def main(args):
    """Search the IOOS Glider DAC and return the dataset ids for all datasets which have updated within the last 24
    hours"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    hours = args.hours
    start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    if args.start_time:
        start_time = parser.parse(args.start_time)
    end_time = datetime.datetime.utcnow()
    if args.end_time:
        end_time = parser.parse(args.end_time)
    north = args.north
    south = args.south
    east = args.east
    west = args.west
    search_string = args.search_string
    response = args.format
    exclude_summaries = args.exclude_summaries
    debug = args.debug

    params = {'min_time': start_time.strftime('%Y-%m-%dT%H:%M'),
              'max_time': end_time.strftime('%Y-%m-%dT%H:%M'),
              'min_lat': south,
              'max_lat': north,
              'min_lon': west,
              'max_lon': east
              }

    client = GdacClient()

    if search_string:
        client.search_datasets(search_for=search_string, params=params)
    else:
        client.search_datasets(params=params)

    if client.datasets.empty:
        logging.warning('No datasets found matching the search criteria')
        return 1

    datasets = client.datasets
    if exclude_summaries:
        datasets = client.datasets.drop('summary', axis=1)

    if response == 'json':
        sys.stdout.write('{:}\n'.format(datasets.to_json(orient='records')))
    elif response == 'csv':
        sys.stdout.write('{:}\n'.format(datasets.to_csv()))
    else:
        columns = ['dataset_id']
        if args.timestamps:
            columns.append('start_date')
            columns.append('end_date')

        if args.wmoid:
            columns.append('wmo_id')

        sys.stdout.write('{:}\n'.format(datasets.reset_index()[columns].to_csv(index=False)))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('--start_time',
                            help='Search start time',
                            type=str)

    arg_parser.add_argument('--end_time',
                            help='Search end time',
                            type=str)

    arg_parser.add_argument('--hours',
                            type=float,
                            help='Number of hours before now',
                            default=24)

    arg_parser.add_argument('-n', '--north',
                            help='Maximum search latitude',
                            default=90.,
                            type=float)

    arg_parser.add_argument('-s', '--south',
                            help='Minimum search latitude',
                            default=-90.,
                            type=float)

    arg_parser.add_argument('-e', '--east',
                            help='Maximum search longitude',
                            default=180.,
                            type=float)

    arg_parser.add_argument('-w', '--west',
                            help='Minimum search longitude',
                            default=-180.,
                            type=float)

    arg_parser.add_argument('--search_string',
                            help='Free format search string',
                            type=str)

    arg_parser.add_argument('-f', '--format',
                            help='Response format',
                            choices=['json', 'csv', 'stdout'],
                            default='stdout')

    arg_parser.add_argument('-t', '--timestamps',
                            help='Include time coverages in stdout',
                            action='store_true')

    arg_parser.add_argument('--wmoid',
                            help='Include WMO IDs if available in stdout',
                            action='store_true')

    arg_parser.add_argument('--exclude_summaries',
                            action='store_true',
                            help='Do not include the summary global attribute in output')

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
