import seaborn as sns
import matplotlib.pyplot as plt
import logging

logging.getLogger(__file__)

month_labels = ['January',
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


def plot_calendar(calendar, center=None, **hm_kwargs):
    """Plot heatmap calendar"""
    if not calendar.columns.name:
        logging.warning('Unknown calendar columns type')
        return

    fontsize = 10.
    if calendar.columns.name == 'day':
        if 'ax' not in hm_kwargs:
            _, hm_kwargs['ax'] = plt.subplots(figsize=(11., 8.5))
    elif calendar.columns.name == 'month':
        if 'ax' not in hm_kwargs:
            _, hm_kwargs['ax'] = plt.subplots(figsize=(8.5, 8.5))
        fontsize = 14.
    else:
        logging.error('Unrecognized calendar columns type: {:}'.format(calendar.columns.name))
        return

    heatmap_kwargs = {'annot': True,
                      'square': True,
                      'cbar': False,
                      'fmt': '.0f',
                      'linewidths': 0.5,
                      'annot_kws': {'fontsize': fontsize}}
    heatmap_kwargs.update(hm_kwargs)

    if center is not None:
        ax = sns.heatmap(calendar, center=center, **heatmap_kwargs)
    else:
        ax = sns.heatmap(calendar, **heatmap_kwargs)

    # Clean up the y and x axes
    ax.set_ylabel('')
    ax.set_xlabel('')

    # x tick labels
    if calendar.columns.name == 'month':
        # Get the current numeric month x tick labels
        old_x_labels = [x.get_text() for x in ax.get_xticklabels()]
        # Translate them to month names
        new_x_labels = [month_labels[int(m) - 1] for m in old_x_labels]
        ax.set_xticklabels(new_x_labels)
        # Rotate to 90 degrees (vertical)
        _ = [xlabel.set_rotation(90) for xlabel in ax.get_xticklabels()]

    # y ticks labels
    if calendar.index.names == ['month']:
        old_y_labels = [y.get_text() for y in ax.get_yticklabels()]
        new_y_labels = [month_labels[int(m) - 1][:3] for m in old_y_labels]
        ax.set_yticklabels(new_y_labels)
    elif calendar.index.names == ['year', 'month']:
        old_y_labels = [y.get_text() for y in ax.get_yticklabels()]
        new_y_labels = []
        for ylabel in old_y_labels:
            y, m = ylabel.split('-')
            new_y_labels.append('{:} {:}'.format(month_labels[int(m) - 1][0:3], y))
        ax.set_yticklabels(new_y_labels)

    # Rotate to 0 degrees (horizontal)
    _ = [ylabel.set_rotation(0) for ylabel in ax.get_yticklabels()]

    return ax

