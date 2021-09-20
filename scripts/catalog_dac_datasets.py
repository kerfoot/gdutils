#!/usr/bin/env python

import argparse
import logging
import os
import sys
import json
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
    deployments = fetch_dac_catalog()
    if not deployments:
        return 1

    # Fire up the GdacClient
    client = GdacClient()

    dataset_ids = [dataset['name'] for dataset in deployments]
    if args.status == 'active':
        dataset_ids = [dataset['name'] for dataset in deployments if not dataset['completed']]
    elif args.status == 'completed':
        dataset_ids = [dataset['name'] for dataset in deployments if dataset['completed']]

    if not args.delayed:
        dataset_ids = [did for did in dataset_ids if not did.endswith('delayed')]

    dataset_ids = sorted(dataset_ids)

    client.search_datasets(dataset_ids=dataset_ids)
    # Write the search results as a csv file
    csv_status_path = os.path.join(args.outputdir, '{:}.csv'.format(args.status))
    logging.info('Writing search results to {:}'.format(csv_status_path))
    client.datasets.to_csv(csv_status_path)

    drop_columns = ['estimated_deploy_date',
                    'estimated_deploy_location',
                    'glider_name',
                    'deployment_dir',
                    'title']
    catalog = []
    for dataset_id, dataset in client.datasets.iterrows():

        deployment = [d for d in deployments if d['name'] == dataset_id]
        if not deployment:
            logging.warning('Deployment not registered at the DAC: {:}'.format(dataset_id))
            continue

        deployment = deployment[0]

        # chop off unnecessary decimal places
        dataset.lat_min = float(Decimal(dataset.lat_min).quantize(Decimal('0.001'), rounding=ROUND_HALF_DOWN))
        dataset.lat_max = float(Decimal(dataset.lat_max).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        dataset.lon_min = float(Decimal(dataset.lon_min).quantize(Decimal('0.001'), rounding=ROUND_HALF_DOWN))
        dataset.lon_max = float(Decimal(dataset.lon_max).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
        dataset.deployment_lat = float(Decimal(dataset.deployment_lat).quantize(Decimal('0.001'), rounding=ROUND_HALF_DOWN))
        dataset.deployment_lon = float(Decimal(dataset.deployment_lon).quantize(Decimal('0.001'), rounding=ROUND_HALF_DOWN))

        # Update the deployment with the results from the GdacClient dataset
        deployment.update(dataset.fillna(False))

        # Chop off the end of the summary
        deployment['summary'] = deployment['summary'][0:deployment['summary'].find('\\n\\ncdm_data_type') - 1]

        [deployment.pop(col, None) for col in drop_columns]

        # Make a copy of the deployment before removing the 'summary' field
        deployment_copy = deployment.copy()

        deployment.pop('summary', None)

        # Get the daily average profile GPS for this dataset
        daily_gps = client.daily_profile_positions.loc[client.daily_profile_positions.dataset_id == dataset_id]
        if daily_gps.empty:
            logging.warning('Dataset contains no profile GPS positions: {:}'.format(dataset_id))
            continue

        dataset_out_path = os.path.join(datasets_path, dataset_id)
        if not os.path.isdir(dataset_out_path):
            logging.info('Creating dataset path: {:}'.format(dataset_out_path))
            try:
                os.mkdir(dataset_out_path)
            except OSError as e:
                logging.error(e)
                continue

        # Create and write the daily averaged GPS position track
        track = latlon_to_geojson_track(daily_gps.latitude, daily_gps.longitude, daily_gps.date)
        track['properties'] = {'datasetd_id': dataset_id}
        daily_track_json_path = os.path.join(dataset_out_path, 'daily_track.json'.format(dataset_id))
        try:
            with open(daily_track_json_path, 'w') as fid:
                json.dump(track, fid)
        except IOError as e:
            logging.error('Error writing daily track GPS {:}: {:}'.format(daily_track_json_path, e))
            continue

        # Create and write the detailed deployment summary
        deployment_json_path = os.path.join(dataset_out_path, 'deployment.json')
        try:
            with open(deployment_json_path, 'w') as fid:
                json.dump(deployment_copy, fid, default=str, sort_keys=True)
        except IOError as e:
            logging.error('Error writing deployment summary {:}: {:}'.format(deployment_json_path, e))
            continue

        catalog.append(deployment)

    status_path = os.path.join(args.outputdir, '{:}.json'.format(args.status))
    try:
        with open(status_path, 'w') as fid:
            json.dump(sorted(catalog, key=itemgetter('end_date'), reverse=True), fid, default=str, sort_keys=True)
    except IOError as e:
        logging.error('Error writing status file: {:}'.format(status_path))
        return 1

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-s', '--status',
                            help='Process all deployments regardless of completed status',
                            choices=['active', 'completed', 'all'],
                            default='active')

    arg_parser.add_argument('-d', '--delayed',
                            help='Process delayed mode datasets also',
                            action='store_true')

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
