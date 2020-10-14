from erddapy import ERDDAP
import pandas as pd
import requests
import logging
import os
from urllib.parse import quote


class ErddapPlotter(object):

    def __init__(self, erddap_url, protocol='tabledap', response='png'):

        self._img_types = ['smallPdf',
                           'pdf',
                           'largePdf',
                           'smallPng',
                           'png',
                           'largePng',
                           'transparentPng']

        self._default_plot_parameters = {'.bgColor=': '0xFFFFFF',
                                         '.color=': '0x000000',
                                         '.colorBar=': 'Rainbow2|C|Linear|||',
                                         '.draw=': 'markers',
                                         '.legend=': 'Bottom',
                                         '.marker=': '6|5',
                                         '.xRange=': '||true|Linear',
                                         '.yRange=': '||false|Linear'}

        if response not in self._img_types:
            raise ValueError('Invalid image response type specified: {:}'.format(response))

        self._erddap_url = erddap_url
        self._protocol = protocol
        self._response = response

        self._plot_query = ''
        self._constraints_query = ''
        self._image_url = ''
        self._last_request = ''

        self._logger = logging.getLogger(os.path.basename(__file__))

        self._e = ERDDAP(self._erddap_url, protocol=self._protocol, response=self._response)

        self._datasets = pd.DataFrame([])
        self.fetch_erddap_datasets()

        self._constraints = {}
        self._plot_parameters = self._default_plot_parameters.copy()

        # self._line_style = {}
        # self._marker_style = {}
        # self._marker_color = {}
        # self._colorbar = {}
        # self._y_range = {}
        # self._x_range = {}
        # self._bg_color = {}
        # self._legend = {}
        # self._zoom = {}

        # self.set_line_style()
        # self.set_marker_style()
        # self.set_marker_color()
        # self.set_colorbar()
        # self.set_y_range()
        # self.set_x_range()
        # self.set_bg_color()
        # self.set_legend_loc()

        self._legend_options = ['Bottom',
                                'Off',
                                'Only']

        self._line_styles = ['lines',
                             'linesAndMarkers',
                             'markers',
                             'sticks',
                             'vectors']

        self._marker_types = ['None',
                              'Plus',
                              'X',
                              'Dot',
                              'Square',
                              'Filled Square',
                              'Circle',
                              'Filled Circle',
                              'Up Triangle',
                              'Filled Up Triangle']

        self._marker_color_codes = ['FFFFFF',
                                    'CCCCCC',
                                    '999999',
                                    '666666',
                                    '000000',
                                    'FF0000',
                                    'FF9900',
                                    'FFFF00',
                                    '99FF00',
                                    '00FF00',
                                    '00FF99',
                                    '00FFFF',
                                    '0099FF',
                                    '0000FF',
                                    '9900FF',
                                    'FF00FF',
                                    'FF99FF']

        self._marker_colors = ['white',
                               'light grey',
                               'grey',
                               'dark grey',
                               'black',
                               'red',
                               'orange',
                               'yellow',
                               'light green',
                               'green',
                               'blue green',
                               'cyan',
                               'blue',
                               'dark blue',
                               'purple',
                               'pink',
                               'light pink']

        self._colors = dict(zip(self._marker_colors, self._marker_color_codes))

        self._continuous_options = ['C',
                                    'D']

        self._scale_options = ['Linear',
                               'Log']

        self._colorbars = ['BlackBlueWhite',
                           'BlackGreenWhite',
                           'BlackRedWhite',
                           'BlackWhite',
                           'BlueWhiteRed',
                           'BlueWideWhiteRed',
                           'LightRainbow',
                           'Ocean',
                           'OceanDepth',
                           'Rainbow',
                           'Rainbow2',
                           'Rainfall',
                           'ReverseRainbow',
                           'RedWhiteBlue',
                           'RedWhiteBlue2',
                           'RedWideWhiteBlue',
                           'Spectrum',
                           'Topography',
                           'TopographyDepth',
                           'WhiteBlueBlack',
                           'WhiteGreenBlack',
                           'WhiteRedBlack',
                           'WhiteBlack',
                           'YellowRed',
                           'KT_algae',
                           'KT_amp',
                           'KT_balance',
                           'KT_curl',
                           'KT_deep',
                           'KT_delta',
                           'KT_dense',
                           'KT_gray',
                           'KT_haline',
                           'KT_ice',
                           'KT_matter',
                           'KT_oxy',
                           'KT_phase',
                           'KT_solar',
                           'KT_speed',
                           'KT_tempo',
                           'KT_thermal',
                           'KT_turbid']

        self._zoom_levels = ['in', 'in2', 'in8', 'out', 'out2', 'out8']

        # Set default plotting parameters
        self.reset_plot_params()

    @property
    def client(self):
        return self._e

    @property
    def response(self):
        return self._e.response

    @response.setter
    def response(self, response_type):
        if response_type not in self._img_types:
            raise ValueError('Invalid image response type specified: {:}'.format(response_type))

        self._response = response_type
        self._e.response = response_type

    @property
    def datasets(self):
        return self._datasets

    @property
    def plot_parameters(self):

        return self._plot_parameters

    @property
    def constraints(self):

        return self._constraints

    @property
    def plot_query(self):

        self.build_plot_query_string()

        return self._plot_query

    @property
    def constraints_query(self):

        self.build_constraints_query_string()

        return self._constraints_query

    @property
    def last_request(self):
        return self._last_request

    @property
    def image_url(self):
        return self._image_url

    @property
    def colorbars(self):
        return self._colorbars

    def fetch_erddap_datasets(self):

        try:

            self._logger.info('Fetching available server datasets: {:}'.format(self._erddap_url))
            url = self._e.get_search_url(response='csv')
            self._last_request = url

            self._logger.debug('Server info: {:}'.format(self._last_request))
            self._datasets = pd.read_csv(url)

            # rename columns more friendly
            columns = {s: s.replace(' ', '_').lower() for s in self._datasets.columns}
            self._datasets.rename(columns=columns, inplace=True)

            # Use dataset_id as the index
            self._datasets.set_index('dataset_id', inplace=True)

        except requests.exceptions.HTTPError as e:
            self._logger.error('Failed to fetch/parse ERDDAP server datasets info: {:} ({:})'.format(url, e))
            return

    def set_bg_color(self, color='white'):
        #   .bgColor:   value (0xAARRGGBB)
        if color not in self._colors:
            return

        self._plot_parameters.update({'.bgColor=': '0x{:}'.format(self._colors[color])})

        # self._bg_color = {'.bgColor=': '0x{:}'.format(self._colors[color])}

    def set_colorbar(self, colorbar='Rainbow2', continuous=None, scale=None, min='', max='',
                     num_sections=''):
        # .colorBar:  palette|continuous|scale|min|max|nSections

        continuous = continuous or self._continuous_options[0]
        scale = scale or self._scale_options[0]

        if colorbar not in self._colorbars:
            return

        if continuous not in self._continuous_options:
            return {}

        if scale not in self._scale_options:
            return {}

        self._plot_parameters.update({'.colorBar=': '{:}|{:}|{:}|{:}|{:}|{:}'.format(colorbar,
                                                                         continuous,
                                                                         scale,
                                                                         min,
                                                                         max,
                                                                         num_sections)})

        # self._colorbar = {'.colorBar=': '{:}|{:}|{:}|{:}|{:}|{:}'.format(colorbar,
        #                                                                  continuous,
        #                                                                  scale,
        #                                                                  min,
        #                                                                  max,
        #                                                                  num_sections)}
        #
        # self._update_plot_params()

    def set_marker_color(self, color='white'):
        #   .color:     value (0xAARRGGBB)
        if color not in self._colors:
            return {}

        self._plot_parameters.update({'.color=': '0x{:}'.format(self._colors[color])})

        # self._marker_color = {'.color=': '0x{:}'.format(self._colors[color])}

        # self._update_plot_params()

    def set_line_style(self, line_style='markers'):
        # .draw:      value (lines|linesAndMarkers|markers|sticks|vectors)

        if line_style not in self._line_styles:
            return {}

        self._plot_parameters.update({'.draw=': line_style})

        # self._line_style = {'.draw=': line_style}

        # self._update_plot_params()

    def set_legend_loc(self, location='Bottom'):
        # .legend:    value (Bottom|Off|Only)

        if location not in self._legend_options:
            return {}

        self._plot_parameters.update({'.legend=': location})

        # self._legend = {'.legend=': location}

        # self._update_plot_params()

    def set_marker_style(self, marker='Circle', marker_size=5):
        # .marker:    markerType|markerSize

        if marker not in self._marker_types:
            return {}

        self._plot_parameters.update({'.marker=': '{:}|{:}'.format(self._marker_types.index(marker), marker_size)})

        # self._marker_style = {'.marker=': '{:}|{:}'.format(self._marker_types.index(marker), marker_size)}

        # self._update_plot_params()

    def set_x_range(self, min_val='', max_val='', ascending=True, scale=None):
        #   .xRange:    min|max|ascending|scale

        scale = scale or self._scale_options[0]

        if scale not in self._scale_options:
            return {}

        self._plot_parameters.update({'.xRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)})

        # self._x_range = {'.xRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)}

        # self._update_plot_params()

    def set_y_range(self, min_val='', max_val='', ascending=False, scale=None):
        #   .yRange:    min|max|ascending|scale

        scale = scale or self._scale_options[0]

        if scale not in self._scale_options:
            return {}

        self._plot_parameters.update({'.yRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)})

        # self._y_range = {'.yRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)}

        # self._update_plot_params()

    def set_zoom(self, zoom_level='in'):

        if zoom_level not in self._zoom_levels:
            return {}

        self._plot_parameters.update({'.zoom=': zoom_level})

        # self._zoom_levels = {'.zoom=': zoom_level}

        # self._update_plot_params()

    def set_trim_pixels(self, num_pixels=10):

        self._plot_parameters.update({'.trim=': str(num_pixels)})

    # def _update_plot_params(self):
    #
    #     self._plot_parameters.update(self._line_style)
    #     self._plot_parameters.update(self._marker_style)
    #     self._plot_parameters.update(self._marker_color)
    #     self._plot_parameters.update(self._colorbar)
    #     self._plot_parameters.update(self._y_range)
    #     self._plot_parameters.update(self._x_range)
    #     self._plot_parameters.update(self._bg_color)
    #     self._plot_parameters.update(self._legend)
    #     self._plot_parameters.update(self._zoom)
    #
    #     self.build_plot_query_string()

    def add_constraint(self, constraint, constraint_value):

        self._constraints[constraint] = constraint_value

    def remove_constraint(self, constraint):

        if not constraint.endswith('='):
            constraint = '{:}='.format(constraint)

        self._constraints.pop(constraint, None)

    def remove_plot_parameter(self, plot_parameter):

        if not plot_parameter.endswith('='):
            plot_parameter = '{:}='.format(plot_parameter)

        self._plot_parameters.pop(plot_parameter, None)

    def reset_plot_params(self):

        self._plot_parameters = self._default_plot_parameters.copy()

        # self._line_style = {}
        # self._marker_style = {}
        # self._marker_color = {}
        # self._colorbar = {}
        # self._y_range = {}
        # self._x_range = {}
        # self._bg_color = {}
        # self._legend = {}

        # Set default plotting parameters
        # self.set_line_style()
        # self.set_marker_style()
        # self.set_marker_color()
        # self.set_colorbar()
        # self.set_y_range()
        # self.set_x_range()
        # self.set_bg_color()
        # self.set_legend_loc()
        # self.set_zoom()
        #
        # self.build_plot_query_string()

    def build_plot_query_string(self):

        self._plot_query = '&'.join(['{:}{:}'.format(k, quote(v)) for k, v in self._plot_parameters.items()])

    def build_constraints_query_string(self):

        self._constraints_query = '&'.join(['{:}{:}'.format(k, quote(v)) for k, v in self._constraints.items()])

    def build_image_request(self, dataset_id, x, y, c=None):

        if dataset_id not in self._datasets.index:
            self._logger.error('Dataset ID {:} does not exist'.format(dataset_id))
            return

        variables = [x, y]
        if c:
            variables.append(c)

        self.build_plot_query_string()
        self.build_constraints_query_string()

        if self._constraints:
            url = '{:}/{:}/{:}.{:}?{:}&{:}&{:}'.format(self._e.server,
                                                       self._e.protocol,
                                                       dataset_id,
                                                       self._response,
                                                       ','.join(variables),
                                                       self._constraints_query,
                                                       self._plot_query)
        else:
            url = '{:}/{:}/{:}.{:}?{:}&{:}'.format(self._e.server,
                                                   self._e.protocol,
                                                   dataset_id,
                                                   self._response,
                                                   ','.join(variables),
                                                   self._plot_query)

        self._image_url = url

        return self._image_url

    def download_image(self, image_url, image_path):

        image_dir = os.path.dirname(image_path)
        if not os.path.isdir(image_dir):
            self._logger.error('Invalid image destination specified: {:}'.format(image_dir))
            return

        self._logger.debug('Image url: {:}'.format(image_url))

        self._logger.info('Fetching and writing image: {:}'.format(image_path))
        r = requests.get(image_url, stream=True)
        if r.status_code != 200:
            self._logger.error('{:} (code={:}'.format(r.reason, r.status_code))
            return
        with open(image_path, 'wb') as f:
            for chunk in r.iter_content():
                f.write(chunk)

            return image_path

    def __repr__(self):
        return '<ErddapPlotter(server={:}, response={:}, num_datasets={:})>'.format(self._e.server,
                                                                                    self._e.response,
                                                                                    len(self._datasets))
