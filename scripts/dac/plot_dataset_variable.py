#!/usr/bin/env python

import argparse
import logging
import os
import sys
from gdutils import GdacClient
from gdutils.plot.plotter import ErddapPlotter


def main(args):
    """Request and download a map of the profile positions for the specified dataset_id"""
    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    dataset_id = args.dataset_id
    img_path = args.directory
    img_type = args.img_type
    marker_color = args.color
    colorbar = args.colorbar
    profiles = args.profiles
    no_legend = args.no_legend
    debug = args.debug
    dataset_variable = args.dataset_variable
    plot_all = args.plot_all
    hours = args.hours
    start_date = args.start_date
    end_date = args.end_date

    # Connect to the GDAC ERDDAP server
    client = GdacClient()
    # Fetch the dataset
    client.search_datasets(dataset_ids=dataset_id)
    if client.datasets.empty:
        logging.error('Dataset not found: {:}'.format(dataset_id))
        return 1

    # Create the ploter
    plotter = ErddapPlotter(client.server, response=img_type)

    # Configure the plot parameters
    plotter.set_colorbar(colorbar=colorbar)
    plotter.set_marker_color(marker_color)
    plotter.set_y_range(min_val=0)
    if no_legend:
        plotter.set_legend_loc('Off')
        plotter.set_trim_pixels()

    # Set up time window
    if not plot_all:
        if not start_date and not end_date:
            plotter.add_constraint('time>=', 'max(time)-{:}hours'.format(hours))
        else:
            if start_date:
                plotter.add_constraint('time>=', start_date)
            if end_date:
                plotter.add_constraint('time<=', end_date)

    ext = img_type[-3:].lower()

    img_url = plotter.build_image_request(dataset_id, 'time', 'depth', dataset_variable)
    image_name = os.path.join(img_path, '{:}_{:}_ts_{:}.{:}'.format(dataset_id, dataset_variable, img_type, ext))
    if profiles:
        img_url = plotter.build_image_request(dataset_id, dataset_variable, 'depth', 'time')
        image_name = os.path.join(img_path, '{:}_{:}_profiles_{:}.{:}'.format(dataset_id, dataset_variable, img_type, ext))
        if marker_color:
            img_url = plotter.build_image_request(dataset_id, dataset_variable, 'depth')

    if debug:
        logging.info('Image request: {:}'.format(img_url))
    else:
        logging.info('Requesting and downloading image {:}'.format(image_name))
        logging.debug('Image url: {:}'.format(img_url))
        img_path = plotter.download_image(img_url, image_name)
        if img_path:
            sys.stdout.write('{:}\n'.format(img_path))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='ERDDAP glider dataset id',
                            type=str)

    arg_parser.add_argument('dataset_variable',
                            help='Dataset variable to plot',
                            type=str)

    arg_parser.add_argument('-a', '--all',
                            dest='plot_all',
                            help='Plot the entire time series',
                            action='store_true')

    arg_parser.add_argument('--hours',
                            help='Plot the last hours of the time series',
                            default=24)

    arg_parser.add_argument('--start_date',
                            help='Plot data >= the specified date')

    arg_parser.add_argument('--end_date',
                            help='Plot data <= the specified date')

    arg_parser.add_argument('-d', '--directory',
                            help='Directory to write the images',
                            type=str)

    arg_parser.add_argument('-f', '--format',
                            help='Image type',
                            dest='img_type',
                            choices=['largePng', 'png', 'smallPng', 'largePdf', 'pdf', 'smallPdf', 'transparentPng'],
                            default='largePng')

    arg_parser.add_argument('-c', '--color',
                            help='Plot the positions using the specified color instead of color coding by timestamp',
                            type=str)

    arg_parser.add_argument('--colorbar',
                            help='Any valid ERDDAP plotting colorbar',
                            type=str,
                            default='Rainbow2')

    arg_parser.add_argument('-p', '--profiles',
                            help='Plot profiles',
                            action='store_true')

    arg_parser.add_argument('--no-legend',
                            action='store_true',
                            dest='no_legend',
                            help='Do not include a legend')

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