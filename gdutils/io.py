import pandas as pd
import os
import logging
import re

logging.getLogger(__file__)

dataset_id_regex = re.compile(r'^.*-\d{8}T\d{4}')


def import_dac_profiles_csv_files(csv_files):
    datasets_daily_profiles = []

    for csv_file in csv_files:

        profile_stats = import_dac_csv(csv_file)

        dataset_profiles_per_day = profile_stats.num_profiles
        dataset_profiles_per_day.name = profile_stats.dataset_id.unique()[0]

        if dataset_profiles_per_day.empty:
            logging.warning('No DAC profiles loaded: {:}'.format(csv_file))
            continue

        datasets_daily_profiles.append(dataset_profiles_per_day)

    daily_profiles = pd.concat(datasets_daily_profiles, axis=1).sort_index()
    daily_profiles.columns.name = 'dataset_id'
    daily_profiles.index.name = 'date'

    return daily_profiles


def import_dac_csv(csv_file):

    fname = os.path.basename(csv_file)
    match = dataset_id_regex.search(fname)
    if not match:
        logging.warning('cannot find dataset id in filename: {:}'.format(fname))
        return pd.DataFrame()

    dataset_id = match.group()

    # Read in the csv
    data = pd.read_csv(csv_file, parse_dates=['time'])

    # Group by day and calculate some results
    profile_stats = data.groupby(data.time.dt.date).agg(
        {'latitude': 'mean', 'longitude': 'mean', 'profile_id': 'count', 'wmo_id': 'mean'}).rename(
        columns={'profile_id': 'num_profiles'})
    profile_stats['dataset_id'] = dataset_id

    return profile_stats


def import_gts_obs_csv_files(csv_files):
    datasets_daily_obs = []

    for csv_file in csv_files:

        obs_stats = import_gts_csv(csv_file)
        if obs_stats.empty:
            logging.warning('No GTS observations loaded: {:}'.format(csv_file))
            continue

        dataset_daily_obs = obs_stats.num_obs
        dataset_daily_obs.name = obs_stats.dataset_id.unique()[0]

        datasets_daily_obs.append(dataset_daily_obs)

    daily_obs = pd.concat(datasets_daily_obs, axis=1).sort_index()
    daily_obs.columns.name = 'dataset_id'
    daily_obs.index.name = 'date'

    return daily_obs


def import_gts_csv(csv_file):

    fname = os.path.basename(csv_file)
    match = dataset_id_regex.search(fname)
    if not match:
        logging.warning('cannot find dataset id in filename: {:}'.format(fname))
        return pd.DataFrame()

    dataset_id = match.group()

    # Read in the csv
    data = pd.read_csv(csv_file, parse_dates=['time'])

    # Group by day and calculate some results
    obs_stats = data.groupby(data.time.dt.date).agg(
        {'platform_code': 'mean', 'platform_type': 'count'}).rename(
        columns = {'platform_code': 'wmo_id', 'platform_type': 'num_obs'})
    obs_stats['dataset_id'] = dataset_id

    return obs_stats


def daily_obs_to_ymd_calendar(obs):

    calendar = obs.groupby([lambda x: x.year, lambda x: x.month, lambda x: x.day]).sum().unstack()

    calendar.columns.name = 'day'
    calendar.index.names = ['year', 'month']

    return calendar


def daily_obs_to_ym_calendar(obs):

    calendar = obs.groupby([lambda x: x.year, lambda x: x.month]).sum().unstack()

    calendar.columns.name = 'month'
    calendar.index.name = 'year'

    return calendar


def daily_obs_to_md_calendar(obs):

    calendar = obs.groupby([lambda x: x.month, lambda x: x.day]).sum().unstack()

    calendar.columns.name = 'day'
    calendar.index.names = 'month'

    return calendar
