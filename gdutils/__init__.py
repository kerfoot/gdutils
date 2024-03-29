import logging
from erddapy import ERDDAP
import pandas as pd
import os
import re
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from math import ceil
import urllib
from urllib.parse import urlsplit, urlunsplit, quote
from requests.exceptions import HTTPError, ConnectionError
from decimal import *
import requests
import urllib3
import io
from gdutils.apis.dac import fetch_dac_catalog_json
from gdutils.geojson import latlon_to_geojson_track


class GdacClient(object):

    def __init__(self, erddap_url=None):

        self._logger = logging.getLogger(os.path.basename(__file__))

        self._erddap_url = erddap_url or 'https://gliders.ioos.us/erddap'
        self._protocol = 'tabledap'
        self._response_type = 'csv'
        self._items_per_page = 1e6
        self._page = 1
        self._client = ERDDAP(server=self._erddap_url, protocol=self._protocol, response=self._response_type)
        self._last_request = None
        self._timeout = (30, None)

        # DataFrame containing all datasets on the ERDDAP server resulting from an Advanced Search of self._erddap_url
        # with no parameters specified
        self._erddap_datasets = pd.DataFrame()

        # DataFrame containing the results of ERDDAP advanced search (endpoints, etc.)
        self._datasets_info = pd.DataFrame()
        # DataFrame containing derived parameters (start/end dates, profile count, etc.)
        self._datasets_summaries = pd.DataFrame()
        self._datasets_profiles = pd.DataFrame()
        self._datasets_days = pd.DataFrame()
        self._daily_profile_positions = pd.DataFrame()

        # Store IOOS Glider DAC API data sets results
        self._api_datasets = pd.DataFrame()
        # Store the merged self.datasets and self._api_datasets
        self._merged_datasets = pd.DataFrame()

        self._profiles_variables = ['time',
                                    'latitude',
                                    'longitude',
                                    'profile_id']

        self._valid_search_kwargs = {'institution',
                                     'ioos_category',
                                     'long_name',
                                     'standard_name',
                                     'variable_name',
                                     'min_lon',
                                     'min_lat',
                                     'max_lon',
                                     'max_lat',
                                     'min_time',
                                     'max_time'}

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

        self._calendar_types = ['datasets',
                                'days',
                                'profiles']

        self.fetch_erddap_datasets()

    @property
    def merged_datasets(self):
        """
        DataFrame containing the merged API/self.datasets records
        """

        return self._merged_datasets

    @property
    def erddap_datasets(self):
        """
        DataFrame containing all data sets resulting from the Advanced Search with no parameters. All data sets on the
        ERDDAP server are returned.
        """
        return self._erddap_datasets

    @property
    def datasets(self):
        """
        DataFrame resulting from the joining of self._datasets_summaries and self._datasets_info
        """
        if self._datasets_summaries.empty:
            return pd.DataFrame()

        return self._datasets_summaries.join(self._datasets_info)

    @property
    def daily_profile_positions(self):
        return self._daily_profile_positions

    @property
    def datasets_profiles(self):
        return self._datasets_profiles

    @property
    def datasets_days(self):
        return self._datasets_days

    @datasets_days.setter
    def datasets_days(self, df):
        if not isinstance(pd.DataFrame(), pd.core.frame.DataFrame):
            self._logger.error('Argument must be a pandas DataFrame')
            return

        self._datasets_days = df

    @property
    def dataset_ids(self):
        if self._datasets_info.empty:
            # self._logger.warning('No data sets found')
            return []

        return list(self._datasets_info.index.values)

    @property
    def gliders(self):
        if self._datasets_summaries.empty:
            # self._logger.warning('No data sets found')
            return []

        return list(self._datasets_summaries.glider.unique())

    @property
    def profiles_per_yyyymmdd(self):
        return self._datasets_profiles.sum(axis=1)

    @property
    def profiles_per_year(self):
        return self._datasets_profiles.sum(axis=1).groupby(lambda x: x.year).sum()

    @property
    def ymd_profiles_calendar(self):
        calendar = self.profiles_per_yyyymmdd.groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.day]).sum().unstack()

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
    def ym_profiles_calendar(self):
        calendar = self.profiles_per_yyyymmdd.groupby([lambda x: x.year, lambda x: x.month]).sum().unstack()

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
    def md_profiles_calendar(self):
        calendar = self.profiles_per_yyyymmdd.groupby([lambda x: x.month, lambda x: x.day]).sum().unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    @property
    def glider_days_per_yyyymmdd(self):
        return self._datasets_days.sum(axis=1)

    @property
    def glider_days_per_year(self):
        return self._datasets_days.sum(axis=1).groupby(lambda x: x.year).sum()

    @property
    def ymd_glider_days_calendar(self):
        # calendar = self.glider_days_per_yyyymmdd.groupby(
        #     [lambda x: x.year, lambda x: x.month, lambda x: x.day]).sum().unstack()
        calendar = self._datasets_days.sum(axis=1).groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.day]).sum().unstack()

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
    def ym_glider_days_calendar(self):
        # calendar = self.glider_days_per_yyyymmdd.groupby([lambda x: x.year, lambda x: x.month]).sum().unstack()
        calendar = self._datasets_days.sum(axis=1).groupby([lambda x: x.year, lambda x: x.month]).sum().unstack()

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
    def md_glider_days_calendar(self):
        # calendar = self.glider_days_per_yyyymmdd.groupby([lambda x: x.month, lambda x: x.day]).sum().unstack()
        calendar = self._datasets_days.sum(axis=1).groupby([lambda x: x.month, lambda x: x.day]).sum().unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    @property
    def deployments_per_yyyymmdd(self):
        return self._datasets_days.sum(axis=1)

    @property
    def deployments_per_year(self):
        return self._datasets_days.groupby(lambda x: x.year).any().sum(axis=1)

    @property
    def ymd_deployments_calendar(self):
        # calendar = self.deployments_per_yyyymmdd.groupby(
        #     [lambda x: x.year, lambda x: x.month, lambda x: x.day]).sum().unstack()
        calendar = self._datasets_days.groupby([lambda x: x.year, lambda x: x.month, lambda x: x.day]).any().sum(
            axis=1).unstack()

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
    def ym_deployments_calendar(self):
        # calendar = self.deployments_per_yyyymmdd.groupby([lambda x: x.year, lambda x: x.month]).sum().unstack()
        calendar = self._datasets_days.groupby([lambda x: x.year, lambda x: x.month]).any().sum(axis=1).unstack()

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
    def md_deployments_calendar(self):
        # calendar = self.deployments_per_yyyymmdd.groupby([lambda x: x.month, lambda x: x.day]).sum().unstack()
        calendar = self._datasets_days.groupby([lambda x: x.month, lambda x: x.day]).any().sum(axis=1).unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    @property
    def yearly_counts(self):

        columns = [self.deployments_per_year, self.glider_days_per_year, self.profiles_per_year]
        totals = pd.DataFrame(columns).transpose().astype('i')
        totals.columns = ['deployments', 'glider days', 'profiles']
        totals.index.name = 'year'

        return totals

    @property
    def e(self):
        """erddapy.ERDDAP client"""
        return self._client

    @property
    def server(self):
        return self._client.server

    @property
    def response_type(self):
        return self._client.response

    @response_type.setter
    def response_type(self, response_type):
        self._client.response = response_type

    @property
    def last_request(self):
        return self._last_request

    def fetch_erddap_datasets(self):
        """
        ERDDAP Advanced search to return all available data sets.  The url is contained in self._erddap_url

        :return:
        self.erddap_datasets: Pandas DataFrame containing the result of the Advanced Search
        """

        try:

            self._logger.info('Fetching available server datasets: {:}'.format(self._erddap_url))
            url = self._client.get_search_url(items_per_page=self._items_per_page)
            self._last_request = url

            self._erddap_datasets = pd.read_csv(url)

            # rename columns more friendly
            columns = {s: s.replace(' ', '_').lower() for s in self._erddap_datasets.columns}
            self._erddap_datasets.rename(columns=columns, inplace=True)

            # Use dataset_id as the index
            self._erddap_datasets.set_index('dataset_id', inplace=True)

        except (requests.exceptions.HTTPError, urllib.error.URLError) as e:
            self._logger.error('Failed to fetch/parse ERDDAP server datasets info: {:} ({:})'.format(url, e))
            return pd.DataFrame()

    def get_glider_datasets(self, glider):

        try:
            if self.datasets.empty:
                self._logger.warning('No data set searched performed. Grabbing gliders from self.erddap_datasets')
                return self._erddap_datasets[self._erddap_datasets.index.str.startswith(glider)]
            else:
                return self.datasets[self.datasets.glider == glider]
        except AttributeError as e:
            self._logger.error('No data sets found for glider {:} ({:})'.format(glider, e))
            return pd.DataFrame([])

    def get_dataset_wmo_id(self, dataset_id):
        """
        Fetch the WMO ID, if assigned and valid, for the specified dataset_id

        :param dataset_id: valid ERDDAP dataset id
        :return: Valid WMO ID or empty string
        """

        wmo_id = None
        if dataset_id not in self._erddap_datasets.index:
            self._logger.warning('Cannot fetch WMO id for invalid dataset id {:}'.format(dataset_id))
            return wmo_id

        # WMO id
        self._logger.info('Fetching {:} WMO ID'.format(dataset_id))
        wmo_id_url = '{:}&distinct()'.format(self.e.get_download_url(dataset_id, variables=['wmo_id']))
        self._last_request = wmo_id_url
        try:
            self._logger.debug('wmo id GET: {:}'.format(self._last_request))
            r = requests.get(wmo_id_url, timeout=self._timeout, stream=True)
            if r.status_code != 200:
                self._logger.error('Request failed [reason={:}, code={:}]'.format(r.reason, r.status_code))
                self._logger.error('Request: {:}'.format(wmo_id_url))
                return None

            wmo_ids = pd.read_csv(io.StringIO(r.text), skiprows=[1])
            if wmo_ids.empty:
                self._logger.warning('No WMO ID found for {:}'.format(dataset_id))
            elif wmo_ids.shape[0] > 1:
                self._logger.warning('Multiple WMO IDs found for {:}'.format(dataset_id))
            else:
                wmo_id = wmo_ids.iloc[0].values.astype('int').astype('str')[0]
                self._logger.info('WMO id harvested in {:0.1f} seconds'.format(r.elapsed.total_seconds()))

        except requests.exceptions.RequestException as e:
            self._logger.error('Failed to fetch WMO ID for {:}: reason={:}'.format(dataset_id, e))
            return None
        except ValueError as e:
            self._logger.warning('Invalid WMO id {:} for {:}: {:}'.format(wmo_id, dataset_id, e))
            return None

        return wmo_id

    def search_datasets(self, params={}, dataset_ids=None, include_delayed_mode=False):
        """Search the ERDDAP server for glider deployment datasets.  Results are stored as pandas DataFrames in:

        self.deployments
        self.datasets

        Equivalent to ERDDAP's Advanced Search.  Searches can be performed by free text, bounding box, time bounds, etc.
        See the erddapy documentation for valid kwargs"""

        url = self._client.get_search_url(items_per_page=self._items_per_page, **params)
        self._logger.debug(url)
        self._last_request = url

        glider_regex = re.compile(r'^(.*)-\d{8}T\d{4}')

        summary_columns = ['glider',
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

        if dataset_ids and not isinstance(dataset_ids, list):
            dataset_ids = [dataset_ids]

        try:
            self._datasets_info = pd.read_csv(url)
            # Drop the allDatasets row
            self._datasets_info.drop(self._datasets_info[self._datasets_info['Dataset ID'] == 'allDatasets'].index,
                                     inplace=True)

            # rename columns more friendly
            columns = {s: s.replace(' ', '_').lower() for s in self._datasets_info.columns}
            self._datasets_info.rename(columns=columns, inplace=True)

            if not include_delayed_mode:
                self._logger.info('Excluding delayed mode datasets')
                self._datasets_info = self._datasets_info[~self._datasets_info.dataset_id.str.endswith('delayed')]

            # Reset the index to start and 0
            self._datasets_info = self._datasets_info.set_index('dataset_id').drop(['griddap', 'wms'], axis=1).replace(
                ['None', None], False)

            if dataset_ids:
                drop_dataset_ids = [did for did, row in self._datasets_info.iterrows() if did not in dataset_ids]
                if drop_dataset_ids:
                    self._datasets_info = self._datasets_info.drop(index=drop_dataset_ids)

        except urllib.error.HTTPError as e:
            self._logger.warning('code={:}: query produced no matching results. (nRows = 0)'.format(e.code))
        except (requests.exceptions.HTTPError, urllib.error.URLError) as e:
            self._logger.error('Failed to fetch/parse ERDDAP server datasets info: {:} ({:})'.format(url, e))
            return

        if self._datasets_info.empty:
            self._logger.warning('No datasets found with specified criteria')
            return

        # Iterate through each data set (except for allDatasets) and grab the info page
        datasets = []
        daily_profiles = []
        datasets_days = []
        avg_profile_pos = []
        for dataset_id, row in self._datasets_info.iterrows():

            # Fetch the WMO id for this dataset, if there is one
            wmo_id = self.get_dataset_wmo_id(dataset_id)
            if not wmo_id:
                wmo_id = ''

            # Harvest all of the profiles contained in the data set (contained in self._profile_variables).
            self._logger.info('Harvesting {:} profiles'.format(dataset_id))

            # Get the data download url for erddap_vars
            try:
                self._logger.debug('Creating download url: {:}'.format(dataset_id))
                data_url = self._client.get_download_url(dataset_id=dataset_id,
                                                         variables=self._profiles_variables)
            except (ConnectionError, ConnectionRefusedError, urllib3.exceptions.MaxRetryError,
                    requests.exceptions.HTTPError) as e:
                self._logger.error('{:} fetch failed: {:}'.format(dataset_id, e))
                continue

            # Fetch the profiles into a pandas dataframe
            try:
                self._logger.debug('Fetching download url: {:}'.format(data_url))
                profiles = pd.read_csv(data_url, skiprows=[1], index_col='time', parse_dates=True,
                                       na_values=['none', 'None']).sort_index()
            except (urllib.error.HTTPError, urllib3.exceptions.ReadTimeoutError, urllib.error.URLError) as e:
                self._logger.error('Failed to fetch {:} profiles: {:}'.format(dataset_id, e))
                continue

            # Group the profile by date, average the latitude and longitude and get a daily count
            profile_stats = profiles.groupby(lambda x: x.date).agg(
                {'latitude': 'mean', 'longitude': 'mean', 'profile_id': 'size'}).rename(
                columns={'profile_id': 'num_profiles'})
            profile_stats['dataset_id'] = dataset_id

            s = profile_stats.num_profiles
            s.name = dataset_id

            avg_profile_pos.append(profile_stats[['dataset_id', 'latitude', 'longitude']])

            daily_profiles.append(s)

            # Create the deployment date range
            d_index = pd.date_range(s.index.min(), s.index.max())
            deployment_days = pd.Series([1 for x in d_index], index=d_index, name=dataset_id)
            datasets_days.append(deployment_days)

            glider_match = glider_regex.match(dataset_id)
            glider = glider_match.groups()[0]

            # First profile time
            dt0 = profiles.index.min()
            # Last profile time
            dt1 = profiles.index.max()
            # Deployment length in days
            days = ceil((dt1 - dt0).total_seconds() / 86400)

            dataset_summary = [glider,
                               dataset_id,
                               str(wmo_id),
                               dt0,
                               dt1,
                               profiles.iloc[0]['latitude'],
                               profiles.iloc[0]['longitude'],
                               profiles.latitude.min(),
                               profiles.latitude.max(),
                               profiles.longitude.min(),
                               profiles.longitude.max(),
                               profiles.shape[0],
                               days
                               ]

            datasets.append(dataset_summary)

        if not datasets:
            self._logger.warning('No datasets returned from search')
            return

        self._datasets_summaries = pd.DataFrame(datasets, columns=summary_columns).set_index('dataset_id').replace(
            ['None', None], False)

        # Create and store the DataFrame containing a 1 on each day the glider was deployed, 0 otherwise
        self._datasets_days = pd.concat(datasets_days, axis=1).sort_index()

        # Create and store the DataFrame containing the number of profiles on each day for each deployment
        self._datasets_profiles = pd.concat(daily_profiles, axis=1).sort_index()
        self._datasets_profiles.index = pd.to_datetime(self._datasets_profiles.index)

        self._daily_profile_positions = pd.concat(avg_profile_pos, axis=0).reset_index().rename(
            columns={'index': 'date'})

        return

    def get_dataset_info(self, dataset_id):
        """Fetch the dataset metadata for the specified dataset_id"""

        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return pd.DataFrame([])

        info = self._datasets_info.loc[dataset_id]
        info.reset_index(inplace=True)
        return info.drop('index', axis=1).transpose()

    def get_dataset_ymd_profiles_calendar(self, dataset_id):
        """
        Return the year/month/day profiles calendar for the specified dataset_id, which must have been returned by
        self.search_datasets.

        :param dataset_id: ERDDAP dataset ID
        :return: year/month/day calendar suitable for plotting with gdutils.plot.plot_calendar
        """
        dataset_profiles = self.get_dataset_profiles(dataset_id)

        calendar = dataset_profiles.dropna().iloc[:, 0].groupby(
            [lambda x: x.year, lambda x: x.month, lambda x: x.day]).count().unstack()

        if calendar.empty:
            return calendar

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

    def get_dataset_ym_profiles_calendar(self, dataset_id):
        """
        Return the year/month profiles calendar for the specified dataset_id, which must have been returned by
        self.search_datasets.

        :param dataset_id: ERDDAP dataset ID
        :return: year/month calendar suitable for plotting with gdutils.plot.plot_calendar
        """
        dataset_profiles = self.get_dataset_profiles(dataset_id)

        calendar = dataset_profiles.dropna().iloc[:, 0].groupby(
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

    def get_dataset_md_profiles_calendar(self, dataset_id):
        """
        Return the month/day profiles calendar for the specified dataset_id, which must have been returned by
        self.search_datasets.

        :param dataset_id: ERDDAP dataset ID
        :return: month/day calendar suitable for plotting with gdutils.plot.plot_calendar
        """

        dataset_profiles = self.get_dataset_profiles(dataset_id)

        calendar = dataset_profiles.dropna().iloc[:, 0].groupby(
            [lambda x: x.month, lambda x: x.day]).count().unstack()

        # Fill in the missing month indices
        calendar.reindex(pd.Index(np.arange(1, 13)))

        for d in np.arange(1, 32):
            if d not in calendar.columns:
                calendar[d] = np.nan

        calendar.sort_index(axis=1, inplace=True)

        calendar.index.set_names('month', inplace=True)
        calendar.columns.set_names('day', inplace=True)

        return calendar

    def check_dataset_exists(self, dataset_id):

        if dataset_id not in self._erddap_datasets.index:
            return False

        return True

    def get_dataset_profiles(self, dataset_id):
        """
        Fetch all profiles (time, latitude, longitude, profile_id) for the specified dataset.  Profiles are sorted
        by ascending time
        """

        if dataset_id not in self._erddap_datasets.index:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return pd.DataFrame()

        url = self._client.get_download_url(dataset_id=dataset_id, variables=self._profiles_variables)

        try:
            return pd.read_csv(url, parse_dates=True, skiprows=[1], index_col='time').sort_index()
        except urllib.error.HTTPError as e:
            self._logger.error('Request: {:}'.format(url))
            return pd.DataFrame()

    def get_dataset_time_coverage(self, dataset_id):
        """Get the time coverage and wmo id (if specified) for specified dataset_id """
        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        return self._datasets_summaries[['start_date', 'end_date', 'wmo_id']].loc[dataset_id]

    def get_dataset_time_series(self, dataset_id, variables, min_time=None, max_time=None):
        """Fetch the variables time-series for the specified dataset_id.  A time window can be specified using min_time
        and max_time, which must be ISO-8601 formatted date strings (i.e.: 'YYYY-mm-ddTHH:MM')

        Parameters
        dataset_id: valid dataset id from self.datasets
        variables: list of one or more valid variables in the dataset

        Options
        min_time: minimum time value formatted as 'YYYY-mm-ddTHH:MM[:SS]'
        max_time: maximum time value formatted as 'YYYY-mm-ddTHH:mm[:SS]'
        """
        if dataset_id not in self._erddap_datasets.index:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        if not isinstance(variables, list):
            variables = [variables]

        all_variables = ['precise_time', 'depth'] + variables
        variables = set(all_variables)

        constraints = {}
        if min_time:
            constraints['precise_time>='] = min_time
        if max_time:
            constraints['precise_time<='] = max_time

        # Not sure why, but pd.read_csv doesn't like percent UNENCODED urls on data requests, so percent escape special
        # characters prior to sending the data request.
        data_url = self.encode_url(
            self._client.get_download_url(dataset_id=dataset_id, variables=variables, constraints=constraints))

        self._last_request = data_url

        return pd.read_csv(data_url, skiprows=[1], parse_dates=True).set_index('precise_time').sort_index()

    def plot_yearly_totals(self, totals_type=None, palette='Blues_d', **kwargs):
        """Bar chart plot of deployments, glider days and profiles, grouped by year"""
        totals = self.yearly_counts.reset_index()

        if totals_type and totals_type not in totals.columns:
            self._logger.error('Invalid category specified: {:}'.format(totals_type))
            return

        if not totals_type:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8.5, 11), sharex=True)
            sns.barplot(x='year', y='deployments', ax=ax1, data=totals, palette=palette, **kwargs)
            sns.barplot(x='year', y='glider days', ax=ax2, data=totals, palette=palette, **kwargs)
            sns.barplot(x='year', y='profiles', ax=ax3, data=totals, palette=palette, **kwargs)

            ax2.set_xlabel('')
            ax1.set_xlabel('')

            ax1.set_title('U.S. IOOS Glider Data Assembly Center')

            return fig, ax1, ax2, ax3

        else:
            ax = sns.barplot(x='year', y=totals_type, data=totals, palette=palette, **kwargs)
            ax.set_title('U.S. IOOS Glider Data Assembly Center')

            return ax.figure, ax

    def export_dataset_daily_tracks(self, output_directory, precision='0.001'):
        """Export geoJson LineString tracks containing an daily averaged GPS position for each dataset contained in
        self.datasets. The json files are written to output_directory, which must be a valid path."""

        if not os.path.isdir(output_directory):
            logging.error('Output directory does not exist: {:}'.format(output_directory))
            return

        for dataset_id in self.dataset_ids:

            dataset_gps = self._daily_profile_positions[self.daily_profile_positions.dataset_id == dataset_id]
            if dataset_gps.empty:
                logging.warning('No daily GPS positions found for dataset ID: {:}'.format(dataset_id))
                continue

            bbox = [float(Decimal(dataset_gps.longitude.min()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
                    float(Decimal(dataset_gps.latitude.min()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
                    float(Decimal(dataset_gps.longitude.max()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
                    float(Decimal(dataset_gps.latitude.max()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN))]
            track = {'type': 'Feature',
                     'bbox': bbox,
                     'geometry': {'type': 'LineString',
                                  'coordinates': [
                                      [float(Decimal(pos.longitude).quantize(Decimal(precision),
                                                                             rounding=ROUND_HALF_DOWN)),
                                       float(Decimal(pos.latitude).quantize(Decimal(precision),
                                                                            rounding=ROUND_HALF_DOWN))]
                                      for i, pos in dataset_gps.iterrows()]},
                     'properties': {'dataset_id': dataset_id}
                     }

            json_path = os.path.join(output_directory, '{:}_track.json'.format(dataset_id))
            with open(json_path, 'w') as fid:
                json.dump(track, fid)

        return

    def get_dataset_track_geojson(self, dataset_id, points=True, precision='0.001'):

        if dataset_id not in self._erddap_datasets.index:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return {}

        profiles = self.get_dataset_profiles(dataset_id)
        if profiles.empty:
            self._logger.warning('No profiles found for dataset ID: {:}'.format(dataset_id))
            return {}

        return latlon_to_geojson_track(profiles.latitude,
                                       profiles.longitude,
                                       profiles.index,
                                       include_points=points,
                                       precision=precision)

    def get_dataset_metadata(self, dataset_id):

        try:
            info_url = self._client.get_info_url(dataset_id)
            return pd.read_csv(info_url)
        except (ConnectionError, ConnectionRefusedError, urllib3.exceptions.MaxRetryError,
                requests.exceptions.HTTPError) as e:
            self._logger.error(e)
            return pd.DataFrame([])

    def get_api_datasets(self):
        """
        Fetch all data sets registered at the U.S IOOS Glider DAC.  The url is stored in gdutils.dac.dac_catalog_url

        :return:
        api_datasets: DataFrame containing the registered data sets
        """

        datasets_json = fetch_dac_catalog_json()

        # self._api_datasets = pd.DataFrame(datasets_json).set_index('name').replace(['None', None, ''], np.nan)
        self._api_datasets = pd.DataFrame(datasets_json).set_index('name')

        boolean_vars = ['archive_safe',
                        'completed',
                        'compliance_check_passed',
                        'delayed_mode']

        for boolean_var in boolean_vars:
            self._api_datasets[boolean_var] = self._api_datasets[boolean_var].fillna(False)

        return self._api_datasets

    def merge_with_api(self, merge_all=True):
        """
        Create a DataFrame containing the inner join of the self._api_datasets and self.datasets and store in
        self.merged_datasets
        """
        _ = self.get_api_datasets()

        if self._api_datasets.empty:
            self._logger.warning('No API registered data sets found')
            return pd.DataFrame()

        if not merge_all:
            self._merged_datasets = self._api_datasets.drop(columns=['wmo_id']).merge(self.datasets, how='right',
                                                                                      left_index=True,
                                                                                      right_index=True)
        else:
            self._merged_datasets = self._api_datasets.drop(columns=['wmo_id']).merge(self.datasets, how='left',
                                                                                      left_index=True,
                                                                                      right_index=True)
        self._merged_datasets['orphaned'] = True
        self._merged_datasets['orphaned'].where(self._merged_datasets.tabledap.isnull(), False, inplace=True)

        # self._merged_datasets.replace(['None', None], np.nan)

    @staticmethod
    def encode_url(data_url):
        """Percent encode special url characters."""
        url_pieces = list(urlsplit(data_url))
        url_pieces[3] = quote(url_pieces[3])

        return urlunsplit(url_pieces)

    def __repr__(self):
        return "<GdacClient(server='{:}', num_datasets={:})>".format(self._client.server,
                                                                     len(self._datasets_info))
