import pytest
import sys, os
import xarray as xr
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import process
from process._common import ProcessArgumentInvalid, ProcessArgumentRequired

FIXTURES_FOLDER = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def minEOTask():
    return process.min.minEOTask(None, "" , None)


@pytest.fixture
def generate_data():
    def _construct(
            data = [[[[0.2,0.8]]]],
            dims = ('t','y','x','band'),
            attrs = {'reduce_by': ['band']},
            as_list = False
        ):
        if as_list:
            return data

        xrdata = xr.DataArray(
            data,
            dims=dims,
            attrs=attrs,
        )
        return xrdata
    return _construct


@pytest.fixture
def execute_min_process(generate_data, minEOTask):
    def wrapped(data_arguments={}, ignore_nodata=None):
        arguments = {}
        if data_arguments is not None: arguments["data"] = generate_data(**data_arguments)
        if ignore_nodata is not None: arguments["ignore_nodata"] = ignore_nodata

        return minEOTask.process(arguments)
    return wrapped


###################################
# tests:
###################################

@pytest.mark.parametrize('data,expected_result,ignore_nodata', [
    ([1,0,3,2], 0, True),
    ([5,2.5,None,-0.7], -0.7, True),
    ([1,0,3,None,2], None, False),
    ([], None, True)
])
def test_examples(execute_min_process, data, expected_result, ignore_nodata):
    """
        Test min process with examples from https://open-eo.github.io/openeo-api/processreference/#min
    """
    data_arguments = {"data": data, "as_list": True}
    result = execute_min_process(data_arguments, ignore_nodata=ignore_nodata)
    assert result == expected_result


@pytest.mark.parametrize('data,expected_data,expected_dims,attrs', [
    ([[[[0.2,0.8]]]], [[[0.2]]], ('t','y','x'), {'reduce_by': ['band']}),
    ([[[[0.1, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, 0.05]]]], [[[0.1, 0.15], [0.05, -0.9]]], ('t','y','x'), {'reduce_by': ['band']}),
    ([[[[0.2,0.8]]]], [[[0.2,0.8]]], ('t','x','band'), {'reduce_by': ['y']}),
    ([[[[0.1, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, 0.05]]]], [[[0.05, 0.1], [-0.9, 0.05]]], ('t','x','band'), {'reduce_by': ['y']}),
])
def test_with_xarray(execute_min_process, generate_data, data, expected_data, expected_dims, attrs):
    """
        Test min process with xarray.DataArrays
    """
    expected_result = generate_data(data=expected_data, dims=expected_dims, attrs=attrs)
    result = execute_min_process({"data": data, "attrs": attrs})
    xr.testing.assert_allclose(result, expected_result)


@pytest.mark.parametrize('data,expected_data,expected_dims,attrs, ignore_nodata', [
    ([[[[np.nan, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, np.nan]]]], [[[0.15, 0.15], [0.05, -0.9]]], ('t','y','x'), {'reduce_by': ['band']}, True),
    ([[[[np.nan, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, np.nan]]]], [[[np.nan, 0.15], [0.05, np.nan]]], ('t','y','x'), {'reduce_by': ['band']}, False)
])
def test_with_xarray_nulls(execute_min_process, generate_data, data, expected_data, expected_dims, attrs, ignore_nodata):
    """
        Test min process with xarray.DataArrays with null in data
    """
    expected_result = generate_data(data=expected_data, dims=expected_dims, attrs=attrs)
    result = execute_min_process({"data": data, "attrs": attrs}, ignore_nodata=ignore_nodata)
    xr.testing.assert_allclose(result, expected_result)
