import requests
import logging
import pandas as pd
from decimal import *

dac_catalog_url = 'https://gliders.ioos.us/providers/api/deployment'

logging.getLogger(__file__)


def fetch_dac_catalog():

    try:
        r = requests.get(dac_catalog_url, timeout=60)
    except requests.exceptions.ReadTimeout as e:
        logging.error(e)
        return []

    if r.status_code == 200:
        return r.json()['results']

    logging.error('Failed to fetch DAC registered deployments: {:}'.format(r.reason))

    return []


def latlon_to_geojson_track(latitudes, longitudes, timestamps, include_points=True, precision='0.001'):

    geojson = {'type': 'FeatureCollection',
               'bbox': latlon_to_bbox(latitudes, longitudes, timestamps, precision=precision)}

    features = [latlon_to_linestring(latitudes, longitudes, timestamps, precision=precision)]

    if include_points:
        points = latlon_to_points(latitudes, longitudes, timestamps, precision=precision)
        features = features + points

    geojson['features'] = features

    return geojson


def latlon_to_linestring(latitudes, longitudes, timestamps, precision='0.001'):
    dataset_gps = pd.DataFrame(index=timestamps)
    dataset_gps['latitude'] = latitudes.values
    dataset_gps['longitude'] = longitudes.values

    track = {'type': 'Feature',
             # 'bbox': bbox,
             'geometry': {'type': 'LineString',
                          'coordinates': [
                              [float(Decimal(pos.longitude).quantize(Decimal(precision),
                                                                     rounding=ROUND_HALF_DOWN)),
                               float(Decimal(pos.latitude).quantize(Decimal(precision),
                                                                    rounding=ROUND_HALF_DOWN))]
                              for i, pos in dataset_gps.iterrows()]},
             'properties': {}
             }

    return track


def latlon_to_points(latitudes, longitudes, timestamps, precision='0.001'):
    dataset_gps = pd.DataFrame(index=timestamps)
    dataset_gps['latitude'] = latitudes.values
    dataset_gps['longitude'] = longitudes.values

    return [{'type': 'Feature',
             'geometry': {'type': 'Point', 'coordinates': [float(Decimal(pos.longitude).quantize(Decimal(precision),
                                                                                                 rounding=ROUND_HALF_DOWN)),
                                                           float(Decimal(pos.latitude).quantize(Decimal(precision),
                                                                                                rounding=ROUND_HALF_DOWN))]},
             'properties': {'ts': i.strftime('%Y-%m-%dT%H:%M:%SZ')}}
            for i, pos in dataset_gps.iterrows()]


def latlon_to_bbox(latitudes, longitudes, timestamps, precision='0.001'):
    dataset_gps = pd.DataFrame(index=timestamps)
    dataset_gps['latitude'] = latitudes.values
    dataset_gps['longitude'] = longitudes.values

    return [float(Decimal(dataset_gps.longitude.min()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
            float(Decimal(dataset_gps.latitude.min()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
            float(Decimal(dataset_gps.longitude.max()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN)),
            float(Decimal(dataset_gps.latitude.max()).quantize(Decimal(precision), rounding=ROUND_HALF_DOWN))]
