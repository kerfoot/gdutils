import pandas as pd
import pytest
from gdutils.dac import fetch_dac_catalog, latlon_to_geojson_track, latlon_to_linestring, latlon_to_points, latlon_to_bbox


@pytest.fixture
def data():
    # lazy testing identified that we need floats, dataframes, and datetimes as input
    yield pd.DataFrame(
        [[-42, 42], [42, -42]],
        columns=["longitudes", "latitudes"],
        index=pd.to_datetime(["2021-02-02", "2021-02-03"]),
        dtype=float,
    )


def test_fetch_dac_catalog():
    # should always return a list
    l = fetch_dac_catalog()
    assert isinstance(l, list)


# TODO: use shapely to test these properly
def test_latlon_to_geojson_track(data):
    geojson = latlon_to_geojson_track(
        data["latitudes"], data["longitudes"], timestamps=data.index)
    assert isinstance(geojson, dict)


def test_latlon_to_linestring(data):
    linestring = latlon_to_linestring(data["latitudes"], data["longitudes"], timestamps=data.index)
    assert isinstance(linestring, dict)

def test_latlon_to_points(data):
    points = latlon_to_points(data["latitudes"], data["longitudes"], timestamps=data.index)
    assert isinstance(points, list)

def test_latlon_to_bbox(data):
    bbox = latlon_to_bbox(data["latitudes"], data["longitudes"], timestamps=data.index)
    assert bbox == [-42.0, -42.0, 42.0, 42.0]