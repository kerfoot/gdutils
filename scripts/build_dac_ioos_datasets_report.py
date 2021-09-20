#!/usr/bin/env python

import logging
import pandas as pd
import argparse
import sys
import re
from gdutils import GdacClient


def main(args):
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    client = GdacClient()
    client.search_datasets(include_delayed_mode=True)

    datasets_report = []

    glider_regex = re.compile(r'^(.*)-(\d{8}T\d{4,})')

    for dataset_id, dataset_metadata in client.datasets.iterrows():

        if dataset_id.endswith('-delayed'):
            logging.info('Skipping delayed mode dataset: {:}'.format(dataset_id))
            continue

        row = {'dataset': '',
               'glider': '',
               'year': '',
               'rt': 'yes',
               'delayed': 'no',
               'ioos_ra': '',
               'funding': '',
               'days': '',
               'profiles': '',
               'wmo_id': None}

        url = client.e.get_info_url(dataset_id)

        logging.info('Fetching dataset info: {:}'.format(url))
        dataset_description = pd.read_csv(url)
        dataset_description.rename(columns={col: col.replace(' ', '_').lower() for col in dataset_description.columns},
                                   inplace=True)

        globals = dataset_description.loc[dataset_description.variable_name == 'NC_GLOBAL']

        funding = globals.loc[globals.attribute_name.str.startswith('acknowledg')]
        ra = globals.loc[globals.attribute_name == 'ioos_regional_association']

        glider_match = glider_regex.match(dataset_id)

        row['dataset'] = '-'.join(glider_match.groups())
        row['year'] = glider_match.groups()[1][0:4]
        if '{:}-delayed'.format(row['dataset']) in client.dataset_ids:
            row['delayed'] = 'yes'

        if not ra.empty:
            row['ioos_ra'] = ra.iloc[0]['value']

        if not funding.empty:
            row['funding'] = ','.join(list(funding.value))

        row['days'] = dataset_metadata.days
        row['profiles'] = dataset_metadata.num_profiles
        row['wmo_id'] = dataset_metadata.wmo_id
        row['glider'] = dataset_metadata.glider

        datasets_report.append(row)

    sys.stdout.write('{:}'.format(pd.DataFrame(datasets_report).to_csv(index=False)))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

    # print(parsed_args)
    # sys.exit(13)

    sys.exit(main(parsed_args))
