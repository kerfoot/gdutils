import numpy as np
import pandas as pd
import logging

logging.getLogger(__file__)


def gts_obs_to_ymd_calendar(obs):

    if obs.empty:
        logging.warning('No observations to create the calendar')
        return pd.DataFrame()

    calendar = obs.set_index('time').platform_code.groupby(
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


def gts_obs_to_ym_calendar(obs):

    if obs.empty:
        logging.warning('No observations to create the calendar')
        return pd.DataFrame()

    calendar = obs.set_index('time').platform_code.groupby(
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


def gts_obs_to_md_calendar(obs):

    if obs.empty:
        logging.warning('No observations to create the calendar')
        return pd.DataFrame()

    calendar = obs.set_index('time').platform_code.groupby(
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



