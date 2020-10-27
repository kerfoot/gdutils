#!/usr/bin/env python

import os
import sys
import argparse
import logging
import datetime
import json
import numpy as np
import pandas as pd
import matplotlib.cm as cm
from dateutil import parser
import matplotlib.pyplot as plt
from gdutils import GdacClient
from gdutils.osmc import DuoProfilesClient
from gdutils.plot import plot_calendar
from gdutils.osmc.calendar import gts_obs_to_ymd_calendar
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker


def main(args):
    """Generate observation calendars for all IOOS Glider DAC datasets that have reported within the last 7 days"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    hours = args.hours
    start_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    if args.start_time:
        start_time = parser.parse(args.start_time)
    end_time = args.end_time
    project = args.project
    north = args.north
    south = args.south
    east = args.east
    west = args.west
    output_dir = args.outputdir
    debug = args.debug
    today = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    if not os.path.isdir(output_dir):
        logging.error('Invalid output directory specified: {:}'.format(output_dir))
        return 1

    img_path = os.path.join(output_dir, project)
    if not debug and not os.path.isdir(img_path):
        try:
            os.mkdir(img_path)
        except OSError as e:
            logging.critical(e)
            return 1

    logging.info('Destination: {:}'.format(img_path))

    params = {'min_time': start_time.strftime('%Y-%m-%d'),
              'min_lat': south,
              'max_lat': north,
              'min_lon': west,
              'max_lon': east
              }

    if end_time:
        params['max_time'] = end_time.strftime('%Y-%m-%d')

    client = GdacClient()
    client.search_datasets(params=params)
    if client.datasets.empty:
        logging.warning('No datasets found matching the search criteria')
        return 0

    logging.info('{:} datasets found.'.format(client.datasets.shape[0]))
    if debug:
        logging.info('Debug switch set. No operations performed')
        return 0

    osmc_client = DuoProfilesClient()

    # Plot the DAC datasets and profiles calendars
    fig, ax = plt.subplots(3, 1, figsize=(11, 8.5))
    # Get deployments
    ymd = client.ymd_deployments_calendar
    plot_calendar(ymd.loc[(2020, 6):(2020, 12), :], ax=ax[0])

    # Get glider days
    ymd = client.ymd_glider_days_calendar
    plot_calendar(ymd.loc[(2020, 6):(2020, 12), :], ax=ax[1])

    # Get profiles
    dac_calendar = client.ymd_profiles_calendar
    plot_calendar(dac_calendar.loc[(2020, 6):(2020, 12), :], ax=ax[2], annot_kws={'fontsize': 8.})

    ax[0].set_title('IOOS DAC Real-Time Deployments')
    ax[1].set_title('IOOS DAC Real-Time Glider Days')
    ax[2].set_title('IOOS DAC Real-Time Profiles')

    fig.suptitle('U.S. IOOS Glider Data Assembly Center Observation Report (As of: {:})'.format(
        datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')))
    plt.tight_layout()

    img_name = os.path.join(img_path, 'obs_calendars.png')
    logging.info('Writing calendars: {:}'.format(img_name))
    plt.savefig(img_name, dpi=300)
    plt.close()

    # Get the GTS obs calendar and plot along with DAC and the difference between the 2
    gts_calendar = osmc_client.get_ymd_obs_calendar(client.datasets)
    diff_calendar = dac_calendar - gts_calendar

    # Plot DAC, GTS and diff
    fig, ax = plt.subplots(3, 1, figsize=(11, 8.5))
    plot_calendar(dac_calendar.loc[(2020, 6):(2020, 12), :].fillna(0), ax=ax[0], annot_kws={'fontsize': 8.})
    plot_calendar(gts_calendar.loc[(2020, 6):(2020, 12), :].fillna(0), ax=ax[1], annot_kws={'fontsize': 8.})
    plot_calendar(diff_calendar.loc[(2020, 6):(2020, 12), :].fillna(0), ax=ax[2], cmap=cm.RdGy, center=0, annot_kws={'fontsize': 8.})

    ax[0].set_title('IOOS DAC Real-Time Profiles')
    ax[1].set_title('GTS Observations')
    ax[2].set_title('DAC Profiles - GTS Observations')

    img_name = os.path.join(img_path, 'dac_gts_obs_calendars.png')
    logging.info('Writing calendars: {:}'.format(img_name))
    plt.savefig(img_name, dpi=300)
    plt.close()

    # Plot the map of all of the tracks contained in client.datasets
    # NaturalEarth Shapefile Feature
    nef_scale = '10m'
    nef_category = 'cultural'
    nef_name = 'admin_0_countries'

    dt0 = parser.parse(params['min_time']).date()
    if end_time:
        dt1 = parser.parse(params['max_time']).date()
        profiles = client.daily_profile_positions.loc[
            (client.daily_profile_positions.date >= dt0) & (client.daily_profile_positions.date <= dt1)]
    else:
        profiles = client.daily_profile_positions.loc[client.daily_profile_positions.date >= dt0]

    # Bounding box/extent [w e s n]
    bbox = np.array([params['min_lon'],
                     params['max_lon'],
                     params['min_lat'],
                     params['max_lat']])

    xticker = mticker.AutoLocator()
    yticker = mticker.AutoLocator()
    xticks = xticker.tick_values(bbox[0], bbox[1])
    yticks = yticker.tick_values(bbox[2], bbox[3])

    map_fig, map_ax = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()))

    # lightblue ocean and tan land
    map_ax.background_patch.set_facecolor('lightblue')
    countries = cfeature.NaturalEarthFeature(category=nef_category, scale=nef_scale, facecolor='none', name=nef_name)
    map_ax.add_feature(countries, linewidth=0.5, edgecolor='black', facecolor='tan')
    states = cfeature.NaturalEarthFeature(category=nef_category, scale=nef_scale, facecolor='none',
                                          name='admin_1_states_provinces')
    map_ax.add_feature(states, linewidth=0.5, edgecolor='black')

    map_ax.set_xticks(xticks)
    map_ax.xaxis.set_major_formatter(LONGITUDE_FORMATTER)
    map_ax.set_yticks(yticks)
    map_ax.yaxis.set_major_formatter(LATITUDE_FORMATTER)
    map_ax.set_extent(bbox, crs=ccrs.PlateCarree())

    calendars_path = os.path.join(img_path, 'dataset_calendars')
    if not os.path.isdir(calendars_path):
        try:
            logging.info('Creating dataset calendars path: {:}'.format(calendars_path))
            os.mkdir(calendars_path)
        except OSError as e:
            logging.error(e)
            return 1

    gts_datasets = []
    for dataset_id, dataset in client.datasets.iterrows():

        dp = profiles.loc[profiles.dataset_id == dataset_id]

        if dp.empty:
            logging.warning('{:}: No profile GPS found'.format(dataset_id))
            continue

        # Plot the daily averaged track
        track = map_ax.plot(dp.longitude, dp.latitude, marker='None')

        # Get the individual dataset DAC profiles calendar
        dac_calendar = client.get_dataset_ymd_profiles_calendar(dataset_id).fillna(0)
        # Get the GTS obs calendar
        dataset_gts_obs = osmc_client.obs.loc[osmc_client.obs.dataset_id == dataset_id]
        dataset['num_gts_obs'] = dataset_gts_obs.shape[0]
        gts_datasets.append(dataset)
        gts_calendar = gts_obs_to_ymd_calendar(dataset_gts_obs).fillna(0)
        if gts_calendar.empty:
            gts_calendar = dac_calendar.copy()
            gts_calendar[:] = 0.
        # Calculate the difference
        diff_calendar = dac_calendar - gts_calendar

        cal_fig, cal_ax = plt.subplots(3, 1, figsize=(11, 8.5))

        _ = plot_calendar(dac_calendar, ax=cal_ax[0], annot_kws={'fontsize': 8.})
        cal_ax[0].set_title('{:}: IOOS Glider DAC Profiles'.format(dataset_id))
        if not gts_calendar.empty:
            _ = plot_calendar(gts_calendar, ax=cal_ax[1], annot_kws={'fontsize': 8.})
            cal_ax[1].set_title('{:}: GTS Observations'.format(dataset_id))
        else:
            logging.warning('No GTS Observations available for {:}'.format(dataset_id))
        _ = plot_calendar(diff_calendar, ax=cal_ax[2], cmap=cm.RdGy, center=0, annot_kws={'fontsize': 8.})
        cal_ax[2].set_title('{:}: DAC Profiles - GTS Observations'.format(dataset_id))

        cal_fig.suptitle('As of: {:}'.format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')))

        dataset_calendar_img_path = os.path.join(calendars_path, 'obs_calendar_{:}.png'.format(dataset_id))
        logging.info('Writing {:}'.format(dataset_calendar_img_path))
        cal_fig.savefig(dataset_calendar_img_path, dpi=300)
        plt.close(cal_fig)

    map_fig.suptitle('IOOS DAC Real-Time Tracks', fontsize=12)
    map_fig.tight_layout()
    img_name = os.path.join(img_path, 'dac_obs_tracks.png')
    map_fig.savefig(img_name, dpi=300)
    plt.close(map_fig)

    datasets_meta = pd.concat(gts_datasets, axis=1).T
    info_path = os.path.join(img_path, 'info.json')
    logging.info('Writing dataset info: {:}'.format(info_path))
    try:
        with open(info_path, 'w') as fid:
            json.dump(datasets_meta.fillna('null').to_dict(orient='records'), fid, indent=4, sort_keys=True,
                      default=str)
    except (IOError, OSError, ValueError) as e:
        logging.error(e)
        return 1

    return 0


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-p', '--project',
                            help='Project name used in output location naming',
                            default='latest',
                            type=str)

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

    arg_parser.add_argument('-o', '--outputdir',
                            help='Location to write calendars',
                            default=os.path.realpath(os.curdir),
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