"""
Glider DAC geoJSON to KML scratch space
"""

import os
import json
import glob
import logging
from jinja2 import Template
from pprint import pprint as pp

status_url = 'https://marine.rutgers.edu/cool/data/gliders/dac/status/dataset.php?dataset_id={:}'
json_path = '/Users/kerfoot/data/gliders/dac/tracks'
template_path = '/Users/kerfoot/data/gliders/dac/kml/templates/tracks.kml'

with open(template_path, 'r', encoding='latin-1') as fid:
    template = Template(fid.read())

json_files = glob.glob(os.path.join(json_path, '*.json'))
json_files.sort()

json_file = json_files[0]

tracks = []
for json_file in json_files:
    with open(json_file, 'r') as fid:

        track = json.load(fid)

        track['features'][0]['properties']['start_ts'] = track['features'][0]['properties']['start_date'].split('+')[0]
        track['features'][0]['properties']['end_ts'] = track['features'][0]['properties']['end_date'].split('+')[0]
        track['features'][0]['properties']['start_date'] = track['features'][0]['properties']['start_date'].split()[0]
        track['features'][0]['properties']['end_date'] = track['features'][0]['properties']['end_date'].split()[0]
        track['features'][0]['properties']['status_url'] = status_url.format(track['features'][0]['properties']['dataset_id'])

        tracks.append(track)

kml = template.render(tracks=tracks)

kml_path, kml_file = os.path.split(template_path)
with open(os.path.join(json_path, 'glider_datasets.kml'), 'w') as fid:
    fid.write(kml)
