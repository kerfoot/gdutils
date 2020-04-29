import logging
from erddapy import ERDDAP
import pandas as pd
import os
import re
import seaborn as sns
import matplotlib.pyplot as plt
from math import ceil
from urllib.parse import urlsplit, urlunsplit, quote
from requests.exceptions import HTTPError, ConnectionError
import urllib3.exceptions


class GdacClient(object):

    def __init__(self, erddap_url=None):

        self._logger = logging.getLogger(os.path.basename(__file__))

        self._erddap_url = erddap_url or 'https://gliders.ioos.us/erddap'
        self._protocol = 'tabledap'
        self._response_type = 'csv'
        self._items_per_page = 1e10
        self._page = 1
        self._client = ERDDAP(server=self._erddap_url, protocol=self._protocol, response=self._response_type)
        self._last_request = None

        # DataFrame containing the results of ERDDAP advanced search (endpoints, etc.)
        self._datasets_info = pd.DataFrame()
        # DataFrame containing dataset_id, start/end dates, profile count, etc.
        self._datasets_summaries = pd.DataFrame()
        self._datasets_profiles = pd.DataFrame()
        self._datasets_days = pd.DataFrame()

        self._profiles_variables = ['time', 'latitude', 'longitude', 'profile_id', 'wmo_id']

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

    @property
    def datasets_info(self):
        return self._datasets_info

    @property
    def datasets_summaries(self):
        return self._datasets_summaries

    @property
    def datasets_profiles(self):
        return self._datasets_profiles

    @property
    def datasets_days(self):
        return self._datasets_days

    @property
    def dataset_ids(self):
        if self._datasets_summaries.empty:
            self._logger.warning('No data sets found')
            return

        return list(self._datasets_info['dataset_id'].values)

    @property
    def gliders(self):
        if self._datasets_summaries.empty:
            self._logger.warning('No data sets found')
            return

        return list(self._datasets_summaries.glider.unique())

    @property
    def profiles_per_yyyymmdd(self):
        return self._datasets_profiles.sum(axis=1)

    @property
    def profiles_per_year(self):
        return self._datasets_profiles.sum(axis=1).groupby(lambda x: x.year).sum()

    @property
    def glider_days_per_yyyymmdd(self):
        return self._datasets_days.sum(axis=1)

    @property
    def glider_days_per_year(self):
        return self._datasets_days.sum(axis=1).groupby(lambda x: x.year).sum()

    @property
    def deployments_per_yyyymmdd(self):
        return self._datasets_days.sum(axis=1)

    @property
    def deployments_per_year(self):
        return self._datasets_days.groupby(lambda x: x.year).any().sum(axis=1)

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

    def get_glider_datasets(self, glider):

        return self._datasets_summaries[self._datasets_summaries.glider == glider].reset_index().drop('index', axis=1)

    def get_deployments_calendar(self, year=None):
        if not year:
            return self._datasets_days.groupby([lambda x: x.year, lambda x: x.month]).any().sum(axis=1).unstack()
        else:
            glider_days_by_yymmdd = self._datasets_days
            years = pd.to_datetime(glider_days_by_yymmdd.index).year.unique()
            if year not in years:
                self._logger.warning('No glider days found in year {:}'.format(year))
                return pd.DataFrame()
            return glider_days_by_yymmdd[pd.to_datetime(glider_days_by_yymmdd.index).year == year].groupby(
                [lambda x: x.month, lambda x: x.day]).any().sum(axis=1).unstack()

    def get_glider_days_calendar(self, year=None):
        if not year:
            return self._datasets_days.sum(axis=1).groupby(
                [lambda x: x.year, lambda x: x.month]).sum().unstack()
        else:
            glider_days_by_yymmdd = self._datasets_days.sum(axis=1)
            years = pd.to_datetime(glider_days_by_yymmdd.index).year.unique()
            if year not in years:
                self._logger.warning('No glider days found in year {:}'.format(year))
                return pd.DataFrame()
            return glider_days_by_yymmdd[pd.to_datetime(glider_days_by_yymmdd.index).year == year].groupby(
                [lambda x: x.month, lambda x: x.day]).sum().unstack()

    def get_profiles_calendar(self, year=None):
        if not year:
            return self._datasets_profiles.sum(axis=1).groupby(
                [lambda x: x.year, lambda x: x.month]).sum().unstack()
        else:
            profiles_by_yymmdd = self._datasets_profiles.sum(axis=1)
            years = pd.to_datetime(profiles_by_yymmdd.index).year.unique()
            if year not in years:
                self._logger.warning('No profiles found in year {:}'.format(year))
                return pd.DataFrame()
            return profiles_by_yymmdd[pd.to_datetime(profiles_by_yymmdd.index).year == year].groupby(
                [lambda x: x.month, lambda x: x.day]).sum().unstack()

    def search_datasets(self, search_for=None, delayedmode=False, **kwargs):
        """Search the ERDDAP server for glider deployment datasets.  Results are stored as pandas DataFrames in:

        self.deployments
        self.datasets

        Equivalent to ERDDAP's Advanced Search.  Searches can be performed by free text, bounding box, time bounds, etc.
        See the erddapy documentation for valid kwargs"""

        url = self._client.get_search_url(search_for=search_for, **kwargs)
        self._last_request = url

        glider_regex = re.compile(r'^(.*)-\d{8}T\d{4}')
        try:
            self._datasets_info = pd.read_csv(url)
            # Drop the allDatasets row
            self._datasets_info.drop(self._datasets_info[self._datasets_info['Dataset ID'] == 'allDatasets'].index,
                                     inplace=True)

            # Reset the index to start and 0
            self._datasets_info.reset_index(inplace=True)
            # Drop the index, griddap wms columns
            self._datasets_info.drop(['index', 'griddap', 'wms'], axis=1, inplace=True)

            # rename columns more friendly
            columns = {s: s.replace(' ', '_').lower() for s in self._datasets_info.columns}
            self._datasets_info.rename(columns=columns, inplace=True)

            if not delayedmode:
                self._datasets_info = self._datasets_info[~self._datasets_info.dataset_id.str.endswith('delayed')]

            # Iterate through each data set (except for allDatasets) and grab the info page
            datasets = []
            daily_profiles = []
            datasets_days = []
            for i, row in self._datasets_info.iterrows():

                if row['dataset_id'] == 'allDatasets':
                    continue

                if delayedmode and not row['dataset_id'].endswith('delayed'):
                    continue
                elif row['dataset_id'].endswith('delayed'):
                    continue

                self._logger.info('Fetching dataset: {:}'.format(row['dataset_id']))

                # Get the data download url for erddap_vars
                try:
                    data_url = self._client.get_download_url(dataset_id=row['dataset_id'],
                                                         variables=self._profiles_variables)
                except (ConnectionError, ConnectionRefusedError, urllib3.exceptions.MaxRetryError) as e:
                    self._logger.error('{:} fetch failed: {:}'.format(row['dataset_id'], e))
                    continue

                # Fetch the profiles into a pandas dataframe
                try:
                    profiles = pd.read_csv(data_url, skiprows=[1], index_col='time', parse_dates=True).sort_index()
                except HTTPError as e:
                    self._logger.error('Failed to fetch profiles: {:}'.format(e))
                    continue

                # Group profiles by yyyy-mm-dd and sum the number of profiles per day
                s = profiles.profile_id.dropna().groupby(lambda x: x.date).count()
                s.name = row['dataset_id']
                daily_profiles.append(s)

                # Create the deployment date range
                d_index = pd.date_range(s.index.min(), s.index.max())
                deployment_days = pd.Series([1 for x in d_index], index=d_index, name=row['dataset_id'])
                datasets_days.append(deployment_days)

                glider_match = glider_regex.match(row['dataset_id'])
                glider = glider_match.groups()[0]

                # First profile time
                dt0 = profiles.index.min()
                # Last profile time
                dt1 = profiles.index.max()
                # Deployment length in days
                days = ceil((dt1 - dt0).total_seconds() / 86400)

                dataset_summary = [glider,
                                   row['dataset_id'],
                                   str(profiles.wmo_id.unique()[0]),
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

            columns = ['glider',
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

            self._datasets_summaries = pd.DataFrame(datasets, columns=columns)

            # Create and store the DataFrame containing a 1 on each day the glider was deployed, 0 otherwise
            self._datasets_days = pd.concat(datasets_days, axis=1).sort_index()

            # Create and store the DataFrame containing the number of profiles on each day for each deployment
            self._datasets_profiles = pd.concat(daily_profiles, axis=1).sort_index()

        except HTTPError as e:
            self._logger.error(e)

        return

    def get_dataset_info(self, dataset_id):
        """Fetch the dataset metadata for the specified dataset_id"""

        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        info = self._datasets_info[self._datasets_info.dataset_id == dataset_id]
        info.reset_index(inplace=True)
        return info.drop('index', axis=1).transpose()

    def get_dataset_profiles(self, dataset_id):
        """Fetch all profiles (time, latitude, longitude, profile_id) for the specified dataset.  Profiles are sorted
        by ascending time"""

        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        url = self._client.get_download_url(dataset_id=dataset_id, variables=self._profiles_variables)

        return pd.read_csv(url, parse_dates=True, skiprows=[1], index_col='time').sort_index()

    def get_dataset_time_coverage(self, dataset_id):
        """Get the time coverage and wmo id (if specified) for specified dataset_id """
        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        return self._datasets_summaries[['dataset_id', 'start_date', 'end_date', 'wmo_id']].iloc[
            self.dataset_ids.index(dataset_id)]

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
        if dataset_id not in self.dataset_ids:
            self._logger.error('Dataset id {:} not found in {:}'.format(dataset_id, self.__repr__()))
            return

        if not isinstance(variables, list):
            variables = [variables]

        all_variables = ['precise_time', 'time', 'depth'] + variables
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

    def plot_datasets_calendar(self, calendar_type, year=None, cmap=None):
        """Heatmap of the specified calendar_type"""
        if calendar_type not in self._calendar_types:
            self._logger.error('Invalid calendar type specified: {:}'.format(calendar_type))
            return

        if calendar_type == 'datasets':
            if not year:
                data = self.get_deployments_calendar()
                title = 'Active Real-Time Datasets'
            else:
                data = self.get_deployments_calendar(year)
                title = 'Active Real-Time Datasets: {:}'.format(year)
        elif calendar_type == 'days':
            if not year:
                data = self.get_glider_days_calendar()
                data.columns = self._months
                title = 'Glider In-Water Days'
            else:
                data = self.get_glider_days_calendar(year)
                title = 'Glider In-Water Days: {:}'.format(year)
        elif calendar_type == 'profiles':
            if not year:
                data = self.get_profiles_calendar()
                data.columns = self._months
                title = 'Real-Time Profiles'
            else:
                data = self.get_profiles_calendar(year)
                title = 'Real-Time Profiles: {:}'.format(year)
        else:
            self._logger.error('Unknown calendar type: {:}'.format(calendar_type))
            return

        if data.empty:
            self._logger.warning('No results found')
            return

        if year:
            data.index = self._months
            plt.figure(figsize=(8.5, 4.))
            cb = True
            annotate = False
        else:
            data.columns = self._months
            plt.figure(figsize=(8.5, 8.5))
            cb = False
            annotate = True

        if cmap:
            ax = sns.heatmap(data, annot=annotate, fmt='.0f', square=True, cbar=cb, linewidths=0.5, cmap=cmap)
        else:
            ax = sns.heatmap(data, annot=annotate, fmt='.0f', square=True, cbar=cb, linewidths=0.5)

        ax.invert_yaxis()
        _ = [ytick.set_rotation(0) for ytick in ax.get_yticklabels()]
        ax.set_title(title)

        return ax

    @staticmethod
    def encode_url(data_url):
        """Percent encode special url characters."""
        url_pieces = list(urlsplit(data_url))
        url_pieces[3] = quote(url_pieces[3])

        return urlunsplit(url_pieces)

    def __repr__(self):
        return "<GdacClient(server='{:}', response='{:}', num_datasets={:})>".format(self._client.server,
                                                                                     self._client.response,
                                                                                     len(self._datasets_info))
