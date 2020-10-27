#!/usr/bin/env python

import argparse
import logging
import os
import sys
import datetime
from gdutils import GdacClient
from gdutils.osmc import DuoProfilesClient
from matplotlib import pyplot as plt


def main(args):
    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    output_dir = args.outputdir
    hours = args.hours
    today = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    client = GdacClient()
    client.search_datasets(params={'min_time': today.strftime('%Y-%m-%d')})

    if client.datasets.shape[0] == 0:
        logging.warning('No recent datasets found (>={:})'.format(today.strftime('%Y-%m-%d')))
        return 0

    osmc_client = DuoProfilesClient()

    # Create and write the totals images
    ax = client.plot_datasets_calendar('datasets')
    img_name = os.path.join(output_dir, 'active_datasets.png')
    logging.info('Writing: {:}'.format(img_name))
    ax.get_figure().savefig(img_name)
    plt.close()

    ax = client.plot_datasets_calendar('days')
    img_name = os.path.join(output_dir, 'active_glider_days.png')
    logging.info('Writing: {:}'.format(img_name))
    ax.get_figure().savefig(img_name)
    plt.close()

    ax = client.plot_datasets_calendar('profiles')
    img_name = os.path.join(output_dir, 'active_glider_profiles.png')
    logging.info('Writing: {:}'.format(img_name))
    ax.get_figure().savefig(img_name)
    plt.close()

    # GTS observations
    ax = osmc_client.plot_gts_obs_calendar(client.datasets, calendar_type='month')
    img_name = os.path.join(output_dir, 'active-gts-obs.png')
    logging.info('Writing: {:}'.format(img_name))
    ax.get_figure().savefig(img_name)
    plt.close()

    # Write the individual dataset profiles calendar
    for r, dataset in client.datasets.iterrows():

        # IOOS Glider DAC
        ax = client.plot_dataset_profiles_calendar(dataset.dataset_id)
        img_name = os.path.join(output_dir, '{:}-profiles.png'.format(dataset.dataset_id))
        logging.info('Writing: {:}'.format(img_name))
        ax.get_figure().savefig(img_name)
        plt.close()

        # GTS observations
        ax = osmc_client.plot_gts_obs_calendar(dataset)
        img_name = os.path.join(output_dir, '{:}-gts-obs.png'.format(dataset.dataset_id))
        logging.info('Writing: {:}'.format(img_name))
        ax.get_figure().savefig(img_name)
        plt.close()

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('cac_files',
                            nargs='*',
                            help='Slocum .cac file to parse')

    arg_parser.add_argument('--hours',
                            type=int,
                            help='Number of hours before now',
                            default=24)

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