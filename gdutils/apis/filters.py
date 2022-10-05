import logging
import pandas as pd

logging.getLogger(__file__)


def filter_all_real_time(df, include_orphaned=False):
    """
    Return the data frame subset of all real-time data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == False)]
    else:
        return df[(df.delayed_mode == False) & (df.orphaned == False)]


def filter_all_delayed_mode(df, include_orphaned=False):
    """
    Return the data frame subset of all delayed-mode data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == True)]
    else:
        return df[(df.delayed_mode == True) & (df.orphaned == False)]


def filter_real_time_active(df, include_orphaned=False):
    """
    Return the data frame subset of real-time active data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == False) & (df.completed == False)]
    else:
        return df[(df.delayed_mode == False) & (df.completed == False) & (df.orphaned == False)]


def filter_real_time_inactive(df, include_orphaned=False):
    """
    Return the data frame subset of real-time inactive (completed) data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == False) & (df.completed == True)]
    else:
        return df[(df.delayed_mode == False) & (df.completed == True) & (df.orphaned == False)]


def filter_delayed_mode_active(df, include_orphaned=False):
    """
    Return the data frame subset of delayed-mode active data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == True) & (df.completed == False)]
    else:
        return df[(df.delayed_mode == True) & (df.completed == False) & (df.orphaned == False)]


def filter_delayed_mode_inactive(df, include_orphaned=False):
    """
    Return the data frame subset of delayed-mode inactive (completed) data sets that are not orphaned.
    :param df: DAC data sets DataFrame
    :param include_orphaned: include (True) or exclude (False) orphaned data sets
    :return: DataFrame
    """
    required_cols = ['delayed_mode',
                     'completed',
                     'orphaned']

    has_required = True
    for col in required_cols:
        if col not in df.columns:
            logging.error('DataFrame is missing column {:}'.format(col))
            had_required = False

    if not has_required:
        return pd.DataFrame()

    if include_orphaned:
        return df[(df.delayed_mode == True) & (df.completed == True)]
    else:
        return df[(df.delayed_mode == True) & (df.completed == True) & (df.orphaned == False)]
