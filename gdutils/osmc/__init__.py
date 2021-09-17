"""OSMC Glider GTS OSMCV4_DUO_PROFILES client"""
import pandas as pd
from erddapy import ERDDAP
import logging
import os
import numpy as np
import requests
import urllib


class DuoProfilesClient(object):

    def __init__(self, erddap_url=None):
        """OSMC ERDDAP OSMCV4_DUO_PROFILES dataset client for retrieving glider profile observations"""
        self._logger = logging.getLogger(os.path.basename(__file__))
        self._erddap_url = erddap_url or 'http://osmc.noaa.gov/erddap'
        self._protocol = 'tabledap'
        self._response_type = 'csv'

        self._datasets = ['OSMCV4_DUO_PROFILES',
                          'OSMC_30day']

        self._dataset_id = self._datasets[0]

        self._client = ERDDAP(server=self._erddap_url, protocol=self._protocol, response=self._response_type)
        self._client.dataset_id = self._dataset_id

        self._last_request = None
        self._profiles = pd.DataFrame()
        self._obs = pd.DataFrame()

        self._dataset_series_fields = ['glider',
                                       'dataset_id',
                                       'wmo_id',
                                       'start_date',
                                       'end_date',
                                       'deployment_lat',
                                       'deployment_lon',
                                       'lat_min',
                                       'lat_max',
                                       'lon_min',
                                       'lon_max',
                                       'num_profiles',
                                       'days']

        self._profile_vars = ['time',
                              'platform_code',
                              'platform_type',
                              'country']

        self._profile_gps_vars = ['time',
                                  'platform_code',
                                  'platform_type',
                                  'country',
                                  'latitude',
                                  'longitude']

        self._months = ['January',
                        'February',
                        'March',
                        'April',
                        'May',
                        'June',
                        'July',
                        'August',
                        'September',
                        'October',
                        'November',
                        'December']

    @property
    def obs(self):
        return self._obs

    @property
    def dataset_id(self):
        return self._client.dataset_id

    @dataset_id.setter
    def dataset_id(self, dataset_id):
        if dataset_id not in self._datasets:
            self._logger.error('Invalid dataset id: {:}'.format(dataset_id))
            return

        self._client.dataset_id = dataset_id

        self._logger.debug('OSMC dataset id: {:}'.format(self._client.dataset_id))

    @property
    def profiles_per_yyyymmdd(self):
        """Daily observation counts for all previously fetched observations"""
        if self._obs.empty:
            self._logger.warning('No GTS observations have been fetched')
            return pd.Series()

        profiles_by_yymmdd = self._obs.set_index('time').platform_code.groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.day]).count()
        profiles_by_yymmdd.name = 'num_profiles'
        profiles_by_yymmdd.index = pd.DatetimeIndex(
            pd.to_datetime(pd.DataFrame(list(profiles_by_yymmdd.index.values), columns=['year', 'month', 'day'])))

        return profiles_by_yymmdd

    @property
    def ymd_observations_calendar(self):

        if self._obs.empty:
            self._logger.warning('No GTS observations have been fetched')
            return pd.Series()

        calendar = self._obs.set_index('time').platform_code.groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.day]).count().unstack()

        # Fill in the missing (yyyy,mm) indices
        years = np.arange(calendar.index.levels[0].min(), calendar.index.levels[0].max() + 1)
        months = np.arange(calendar.index.levels[1].min(), calendar.index.levels[1].max() + 1)

        calendar.reindex(pd.MultiIndex.from_product([years, months]))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names(['year', 'month'], inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    @property
    def ym_observations_calendar(self):

        if self._obs.empty:
            self._logger.warning('No GTS observations have been fetched')
            return pd.Series()

        calendar = self._obs.set_index('time').platform_code.groupby(
            [lambda x: x.year, lambda x: x.month]).count().unstack()

        # Fill in the missing year indices
        years = np.arange(calendar.index.min(), calendar.index.max() + 1)
        calendar.reindex(pd.Index(years))

        for d in np.arange(1, 13):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('year', inplace=True)
        calendar.columns.set_names('month', inplace=True)

        return calendar

    @property
    def md_observations_calendar(self):

        if self._obs.empty:
            self._logger.warning('No GTS observations have been fetched')
            return pd.Series()

        calendar = self._obs.set_index('time').platform_code.groupby(
            [lambda x: x.year, lambda x: x.month]).count().unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    def get_profiles_by_wmo_id(self, wmo_id, start_date, end_date, gps=False):

        constraints = {'platform_code=': wmo_id,
                       'time>=': start_date,
                       'time<=': end_date}

        obs_vars = self._profile_vars
        if gps:
            obs_vars = self._profile_gps_vars

        try:
            data_url = self._client.get_download_url(variables=obs_vars,
                                                     constraints=constraints)
        except requests.exceptions.HTTPError as e:
            self._logger.warning(e)
            return pd.DataFrame()

        data_url = '{:}&distinct()'.format(data_url)

        self._last_request = data_url
        self._logger.debug('Request: {:}'.format(self._last_request))

        try:
            profiles = pd.read_csv(data_url, skiprows=[1], parse_dates=True, index_col='time')
        except urllib.error.HTTPError as e:
            self._logger.error('Fetch of WMO id {:} failed: {:} for {:}'.format(wmo_id, e, data_url))
            return pd.DataFrame()

        # profiles.time = pd.to_datetime(profiles.time)

        # Store the profiles DataFrame so we don't have to request it again
        self._profiles = profiles

        return profiles

    def get_dataset_profiles(self, datasets):
        """Fetch the GTS profiles for the specified dataset.  Profiles are searched by wmo ID (platform_code) and
        dataset start_date and end_date.  Returns a pandas DataFrame"""

        if isinstance(datasets, pd.Series):
            datasets = datasets.to_frame().T

        all_profiles = []
        for dataset_id, row in datasets.iterrows():

            if row.wmo_id == 'None':
                self._logger.warning('Skipping GTS fetch for {:}: No wmo id'.format(dataset_id))
                continue
            else:
                self._logger.info('Fetching GTS obs for {:}'.format(dataset_id))
            dataset_profiles = self.get_profiles_by_wmo_id(row['wmo_id'],
                                                           row['start_date'],
                                                           row['end_date'])

            dataset_profiles['dataset_id'] = dataset_id

            all_profiles.append(dataset_profiles)

        self._obs = pd.concat(all_profiles)
        return self._obs

    def get_ymd_obs_calendar(self, datasets):

        profiles = self.get_dataset_profiles(datasets)
        if profiles.empty:
            self._logger.warning('No GTS obs found')
            return

        try:
            # calendar = profiles.set_index('time').platform_code.groupby(
            #     [lambda x: x.year, lambda x: x.month, lambda x: x.day]).count().unstack()
            calendar = profiles.platform_code.groupby(
                [lambda x: x.year, lambda x: x.month, lambda x: x.day]).count().unstack()
        except KeyError as e:
            self._logger.error(e)

        # Fill in the missing (yyyy,mm) indices
        years = np.arange(calendar.index.levels[0].min(), calendar.index.levels[0].max() + 1)
        months = np.arange(calendar.index.levels[1].min(), calendar.index.levels[1].max() + 1)

        calendar.reindex(pd.MultiIndex.from_product([years, months]))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names(['year', 'month'], inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    def get_ym_obs_calendar(self, datasets):

        profiles = self.get_dataset_profiles(datasets)
        if profiles.empty:
            self._logger.warning('No GTS obs found')
            return

        # calendar = profiles.set_index('time').platform_code.groupby(
        #     [lambda x: x.year, lambda x: x.month]).count().unstack()

        calendar = profiles.platform_code.groupby([lambda x: x.year, lambda x: x.month]).count().unstack()

        # Fill in the missing year indices
        years = np.arange(calendar.index.min(), calendar.index.max() + 1)
        calendar.reindex(pd.Index(years))

        for d in np.arange(1, 13):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('year', inplace=True)
        calendar.columns.set_names('month', inplace=True)

        return calendar

    def get_md_obs_calendar(self, datasets):

        profiles = self.get_dataset_profiles(datasets)
        if profiles.empty:
            self._logger.warning('No GTS obs found')
            return

        # calendar = profiles.set_index('time').platform_code.groupby(
        #     [lambda x: x.month, lambda x: x.day]).count().unstack()

        calendar = profiles.platform_code.groupby([lambda x: x.month, lambda x: x.day]).count().unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    def __repr__(self):
        return "<DuoProfilesClient(server='{:}', response='{:}', dataset_id={:})>".format(self._client.server,
                                                                                          self._client.response,
                                                                                          self._client.dataset_id)
