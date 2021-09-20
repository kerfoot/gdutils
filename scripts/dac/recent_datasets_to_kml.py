"""
Glider DAC geoJSON to KML scratch space
"""

import os
import json
import sys
import logging
from jinja2 import Template
import argparse


def main(args):
    """
    Convert the specified geoJSON files to kml and print to stdout
    """
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    status_url = 'https://marine.rutgers.edu/cool/data/gliders/dac/status/dataset.php?dataset_id={:}'
    json_files = args.json_files
    template = args.template

    if not os.path.isfile(template):
        logging.error('Invalid kml template specified: {:}'.format(template))
        return 1

    with open(template, 'r', encoding='latin-1') as fid:
        template = Template(fid.read())
    
    if not json_files:
        logging.warning('No geoJSON files specified')
        return 1

    json_files.sort()

    tracks = []
    for json_file in json_files:
        with open(json_file, 'r') as fid:
    
            track = json.load(fid)
    
            track['features'][0]['properties']['start_ts'] = track['features'][0]['properties']['start_date'].split('+')[0]
            track['features'][0]['properties']['end_ts'] = track['features'][0]['properties']['end_date'].split('+')[0]
            track['features'][0]['properties']['start_date'] = track['features'][0]['properties']['start_date'].split()[0]
            track['features'][0]['properties']['end_date'] = track['features'][0]['properties']['end_date'].split()[0]
            track['features'][0]['properties']['status_url'] = status_url.format(track['features'][0]['properties']['dataset_id'])
    
            tracks.append(track)
    
    kml = template.render(tracks=tracks)
    
    sys.stdout.write('{:}\n'.format(kml))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('json_files',
                            nargs='+',
                            help='geoJSON track files')

    arg_parser.add_argument('-t', '--template',
                            help='jinja2 kml template file',
                            default='/home/coolgroup/slocum/dac/kml/tracks_template.kml')

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))
