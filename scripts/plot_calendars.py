#!/usr/bin/env python

import argparse
import sys
import os
import logging
import datetime
import dateutil
import pytz
from gdutils import GdacClient
from gdutils.plot import plot_calendar
import matplotlib.pyplot as plt


def main(args):
    """
    Search the IOOS Glider DAC for data sets matching the search criteria and write the deployments, glider days and
    profiles calendars.
    """

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)
    delayed = args.delayed
    hours = args.hours
    dt0 = None
    if hours > 0:
        dt0 = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    elif args.start_time:
        dt0 = dateutil.parser.parse(args.start_time).replace(tzinfo=pytz.UTC)

    dt1 = datetime.datetime.utcnow()
    if args.end_time:
        dt1 = dateutil.parser.parse(args.end_time).replace(tzinfo=pytz.UTC)
    north = args.north
    south = args.south
    east = args.east
    west = args.west
    search_string = args.search_string
    debug = args.debug
    title = args.title or ''

    img_path = args.img_path or os.path.realpath(os.path.curdir)
    logging.info('Writing imagery to {:}'.format(img_path))
    if not os.path.isdir(img_path):
        logging.error('Destination does not exist: {:}'.format(img_path))
        return 1

    # Search parameters dict
    params = {'min_time': dt0,
              'max_time': dt1,
              'min_lat': south,
              'max_lat': north,
              'min_lon': west,
              'max_lon': east
              }

    # Create an instance of the GdacClient class
    client = GdacClient()

    # Search the DAC for available data sets
    client.search_datasets(search_for=search_string, params=params, include_delayed_mode=delayed)

    # Print the data set ids only and exist if -x
    if debug:
        logging.info('{:} data sets matching the search criteria'.format(client.datasets.shape[0]))
        for dataset_id in client.dataset_ids:
            sys.stdout.write('{:}\n'.format(dataset_id))
            return 0

    # Set cutoff year month tuples
    ym0 = (dt0.year, dt0.month)
    ym1 = (dt1.year, dt1.month)
    # Map month numbers to strings

    # deployments calendar
    calendar = client.ymd_deployments_calendar.loc[ym0:ym1]
    ax = plot_calendar(calendar)
    ax.set_title('{:} Deployments: {:} - {:}'.format(title, dt0.strftime('%b %d, %Y'), dt1.strftime('%b %d, %Y')))
    img_name = os.path.join(img_path, 'ymd_deployments.png')
    plt.savefig(img_name, bbox_inches='tight', dpi=300)

    # glider days calendar
    calendar = client.ymd_glider_days_calendar.loc[ym0:ym1]
    ax = plot_calendar(calendar)
    ax.set_title('{:} Glider Days: {:} - {:}'.format(title, dt0.strftime('%b %d, %Y'), dt1.strftime('%b %d, %Y')))
    img_name = os.path.join(img_path, 'ymd_gliderdays.png')
    plt.savefig(img_name, bbox_inches='tight', dpi=300)

    # profiles calendar
    calendar = client.ymd_profiles_calendar.loc[ym0:ym1]
    ax = plot_calendar(calendar, annot_kws={'fontsize': 6})
    ax.set_title('{:} Profiles: {:} - {:}'.format(title, dt0.strftime('%b %d, %Y'), dt1.strftime('%b %d, %Y')))
    img_name = os.path.join(img_path, 'ymd_profiles.png')
    plt.savefig(img_name, bbox_inches='tight', dpi=300)

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-o', '--output_path',
                            dest='img_path',
                            type=str,
                            help='Image write destination (must exist)')

    arg_parser.add_argument('--title',
                            type=str,
                            help='Text to be prepended to the figure title for each of the 3 figures written')

    arg_parser.add_argument('-d', '--delayed',
                            help='Include delayed mode data sets',
                            action='store_true')

    arg_parser.add_argument('--start_time',
                            help='Search start time',
                            type=str)

    arg_parser.add_argument('--end_time',
                            help='Search end time',
                            type=str)

    arg_parser.add_argument('--hours',
                            type=float,
                            help='Number of hours before now',
                            default=0)

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