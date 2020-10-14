# Graph parameters
#   .bgColor:   value (0xAARRGGBB)
#   .colorBar:  palette|continuous|scale|min|max|nSections
#   .color:     value (0xAARRGGBB)
#   .draw:      value (lines|linesAndMarkers|markers|sticks|vectors)
#   .font:      scaleFactor
#   .land:      value (over|under)
#   .legend:    value (Bottom|Off|Only)
#   .marker:    markerType|markerSize
#   .size:      width|height
#   .trim:      trimPixels
#   .vec:       value
#   .xRange:    min|max|ascending|scale
#   .yRange:    min|max|ascending|scale

legend_options = ['Bottom',
                  'Off',
                  'Only']

line_styles = ['lines',
               'linesAndMarkers',
               'markers',
               'sticks',
               'vectors']

marker_types = ['None',
                'Plus',
                'X',
                'Dot',
                'Square',
                'Filled Square',
                'Circle',
                'Filled Circle',
                'Up Triangle',
                'Filled Up Triangle']

marker_color_codes = ['FFFFFF',
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

marker_colors = ['white',
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

colors = dict(zip(marker_colors, marker_color_codes))

continuous_options = ['C',
                      'D']

scale_options = ['Linear',
                 'Log']

colorbars = ['BlackBlueWhite',
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


def set_bg_color(color='white'):
    #   .bgColor:   value (0xAARRGGBB)
    if color not in colors:
        return

    return {'.bgColor=': '0x{:}'.format(colors[color])}


def set_colorbar(colorbar, continuous=continuous_options[0], scale=scale_options[0], minval='', maxval='',
                 num_sections=''):
    # .colorBar:  palette|continuous|scale|min|max|nSections

    if colorbar not in colorbars:
        return

    if continuous not in continuous_options:
        return {}

    if scale not in scale_options:
        return {}

    return {'.colorBar=': '{:}|{:}|{:}|{:}|{:}|{:}'.format(colorbar,
                                                           continuous,
                                                           scale,
                                                           minval,
                                                           maxval,
                                                           num_sections)}


def set_marker_color(color='white'):
    #   .color:     value (0xAARRGGBB)
    if color not in colors:
        return {}

    return {'.color=': '0x{:}'.format(colors[color])}


def set_line_style(line_style='markers'):
    # .draw:      value (lines|linesAndMarkers|markers|sticks|vectors)

    if line_style not in line_styles:
        return {}

    return {'.draw=': line_style}


def set_legend_loc(location='Bottom'):
    # .legend:    value (Bottom|Off|Only)

    if location not in legend_options:
        return {}

    return {'.legend=': location}


def set_marker_style(marker='Circle', marker_size=5):
    # .marker:    markerType|markerSize

    if marker not in marker_types:
        return {}

    return {'.marker=': '{:}|{:}'.format(marker_types.index(marker), marker_size)}


def set_x_range(min_val='', max_val='', ascending=True, scale=scale_options[0]):
    #   .xRange:    min|max|ascending|scale

    if scale not in scale_options:
        return {}

    return {'.xRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)}


def set_y_range(min_val='', max_val='', ascending=True, scale=scale_options[0]):
    #   .yRange:    min|max|ascending|scale

    if scale not in scale_options:
        return {}

    return {'.yRange=': '{:}|{:}|{:}|{:}'.format(min_val, max_val, str(ascending).lower(), scale)}
