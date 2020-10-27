#!/usr/bin/env python

import argparse
import logging
import sys
import pandas as pd
from gdutils import GdacClient
from gdutils.dac import fetch_dac_catalog


def main(args):
    """Get IOOS Glider Data Assembly Center dataset metadata records for the specified dataset_id(s)"""

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    dataset_ids = args.dataset_ids
    exclude_summaries = args.exclude_summaries
    response = args.format

    # Fetch the DAC registered deployments
    deployments = fetch_dac_catalog()
    if not deployments:
        return 1

    # Fire up the GdacClient
    client = GdacClient()

    client.search_datasets(dataset_ids=dataset_ids)
    if client.datasets.empty:
        for dataset_id in dataset_ids:
            logging.warning('Dataset not found: {:}'.format(dataset_id))
        return 1

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

        # Update the deployment with the results from the GdacClient dataset
        deployment.update(dataset.fillna(False))

        # Chop off the end of the summary
        deployment['summary'] = deployment['summary'][0:deployment['summary'].find('\\n\\ncdm_data_type') - 1]

        [deployment.pop(col, None) for col in drop_columns]

        # Make a copy of the deployment before removing the 'summary' field
        deployment_copy = deployment.copy()

        if exclude_summaries:
            deployment.pop('summary', None)

        catalog.append(deployment)

    if len(catalog) == 0:
        logging.warning('No dataset(s) found.')
        return 1

    datasets = pd.DataFrame(catalog).set_index('name')

    if response == 'json':
        sys.stdout.write('{:}\n'.format(datasets.to_json(orient='records')))
    elif response == 'csv':
        sys.stdout.write('{:}\n'.format(datasets.to_csv()))

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_ids',
                            help='ERDDAP dataset ids',
                            nargs='+')

    arg_parser.add_argument('-f', '--format',
                            help='Response format',
                            choices=['json', 'csv'],
                            default='json')

    arg_parser.add_argument('--exclude_summaries',
                            action='store_true',
                            help='Include the summary global attribute in output')

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))