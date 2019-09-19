import json
import pytest
import re
import urllib.parse as urlparse
import responses
import json
from copy import deepcopy
import sys, os

os.environ["SENTINELHUB_INSTANCE_ID"] = "fake_sentinel_hub_instance_id"
os.environ["SENTINELHUB_LAYER_ID"] = "S2L1C"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import process
from process._common import ProcessArgumentInvalid
FIXTURES_FOLDER = os.path.join(os.path.dirname(__file__), 'fixtures')


###################################
# utility methods:
###################################


def assert_wcs_bbox_matches(wcs_params, crs, west, east, north, south):
    assert wcs_params['crs'] == crs

    if crs == 'EPSG:4326':
        if wcs_params['version'] == '1.1.2':
            assert wcs_params['bbox'] == '{south},{west},{north},{east}'.format(west=west, east=east, north=north, south=south)
        elif wcs_params['version'] == '1.0.0':
            assert wcs_params['bbox'] == '{west},{south},{east},{north}'.format(west=west, east=east, north=north, south=south)
        else:
            assert False, "The tests do not know how to handle this version!"
    else:
        assert False, "The tests do not know how to handle this CRS!"


def query_params_from_url(url):
    parsed = urlparse.urlparse(url)
    unprocessed_params = urlparse.parse_qs(parsed.query)
    result = {}
    for k in unprocessed_params:
        result[k.lower()] = unprocessed_params[k][0]
    return result

def modify_value(data,key,value):
    data2 = deepcopy(data)
    data2[key] = value
    return data2


###################################
# fixtures:
###################################


@pytest.fixture
def response_01():
    filename = os.path.join(FIXTURES_FOLDER, 'response_load_collection01.json')
    assert os.path.isfile(filename), "Please run load_fixtures.sh!"
    return json.load(open(filename))

@pytest.fixture
def response_02():
    filename = os.path.join(FIXTURES_FOLDER, 'response_load_collection02.tiff')
    assert os.path.isfile(filename), "Please run load_fixtures.sh!"
    return open(filename, 'rb').read()

@pytest.fixture
def arguments():
    bbox = {
        "west": 12.32271,
        "east": 12.33572,
        "north": 42.07112,
        "south": 42.06347
    }
    data = {
        "id": "S2L1C",
        "spatial_extent": bbox,
        "temporal_extent": ["2019-08-16", "2019-08-18"],
    }

    return data

@pytest.fixture
def load_collectionEOTask(arguments):
    return process.load_collection.load_collectionEOTask(arguments, "", None)

@pytest.fixture
def set_responses(response_01,response_02):
    sh_url_regex01 = re.compile('^.*sentinel-hub.com/ogc/wfs/.*$')
    responses.add(
        responses.GET,
        sh_url_regex01,
        body=json.dumps(response_01),
        match_querystring=True,
        status=200,
    )

    sh_url_regex02 = re.compile('^.*sentinel-hub.com/ogc/wcs/.*$')
    responses.add(
        responses.GET,
        sh_url_regex02,
        body=response_02,
        match_querystring=True,
        status=200,
    )


###################################
# tests:
###################################

@responses.activate
def test_correct(response_01, response_02, arguments, load_collectionEOTask, set_responses):
    """
        Test load_collection process with correct parameters
    """
    result = load_collectionEOTask.process(arguments)
    assert len(responses.calls) == 2
    params = query_params_from_url(responses.calls[1].request.url)
    assert_wcs_bbox_matches(params, 'EPSG:4326', **arguments["spatial_extent"])

@responses.activate
def test_collection_id(response_01, response_02, arguments, load_collectionEOTask, set_responses):
    """
        Test load_collection process with incorrect collection id
    """
    arguments["id"] = "non-existent"

    with pytest.raises(ProcessArgumentInvalid) as ex:
        result = load_collectionEOTask.process(arguments)

    assert ex.value.args[0] == "The argument 'id' in process 'load_collection' is invalid: unknown collection id"

@responses.activate
def test_temporal_extent(response_01, response_02, arguments, load_collectionEOTask, set_responses):
    """
        Test load_collection process with incorrect temporal_extent
    """
    arguments["temporal_extent"] = [None,None]

    with pytest.raises(ProcessArgumentInvalid) as ex:
        result = load_collectionEOTask.process(arguments)

    assert ex.value.args[0] == "The argument 'temporal_extent' in process 'load_collection' is invalid: Only one boundary can be set to null."

    arguments["temporal_extent"] = "A date"

    with pytest.raises(ProcessArgumentInvalid) as ex:
        result = load_collectionEOTask.process(arguments)

    assert ex.value.args[0] == "The argument 'temporal_extent' in process 'load_collection' is invalid: The interval has to be specified as an array with exactly two elements."


