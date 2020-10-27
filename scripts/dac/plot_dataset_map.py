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
    zoom_level = args.zoom
    no_legend = args.no_legend
    debug = args.debug

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
    plotter.set_y_range(ascending=False)
    plotter.set_colorbar(colorbar=colorbar)
    plotter.set_marker_color(marker_color)
    if zoom_level:
        plotter.set_zoom(zoom_level)
    if no_legend:
        plotter.set_legend_loc('Off')
        plotter.set_trim_pixels()

    map_url = plotter.build_image_request(dataset_id, 'longitude', 'latitude', 'time')
    if marker_color:
        map_url = plotter.build_image_request(dataset_id, 'longitude', 'latitude')

    ext = img_type[-3:].lower()

    image_name = os.path.join(img_path, '{:}_track_map_{:}.{:}'.format(dataset_id, img_type, ext))

    if debug:
        logging.info('Image request: {:}'.format(map_url))
    else:
        logging.info('Requesting and dowloading image {:}'.format(image_name))
        logging.debug('Image url: {:}'.format(map_url))
        img_path = plotter.download_image(map_url, image_name)
        if img_path:
            sys.stdout.write('{:}\n'.format(img_path))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='ERDDAP glider dataset id',
                            type=str)

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

    arg_parser.add_argument('-z', '--zoom',
                            help='Set map zoom level',
                            choices=['in', 'in2', 'in8', 'out', 'out2', 'out8'])

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