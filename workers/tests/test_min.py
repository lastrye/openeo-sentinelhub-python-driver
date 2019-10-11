import pytest
import sys, os
import xarray as xr

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


def test_with_xarray(execute_min_process, generate_data):
    """
        Test min process with xarray.DataArrays as we typically use it
    """
    expected_result = generate_data(data=[[[0.2]]], dims=('t','y','x'))
    result = execute_min_process()

    xr.testing.assert_allclose(result, expected_result)

    expected_result = generate_data(data=[[[0.2,0.8]]], dims=('t','x','band'), attrs={'reduce_by': ['y']})
    data_arguments = {"attrs": {'reduce_by': ['y']}}
    result = execute_min_process(data_arguments)

    xr.testing.assert_allclose(result, expected_result)

    data = [[[[0.1, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, 0.05]]]]
    data_arguments = {"data": data}
    expected_data = [[[0.1, 0.15], [0.05, -0.9]]]
    expected_result = generate_data(data=expected_data, dims=('t','y','x'))
    result = execute_min_process(data_arguments)

    xr.testing.assert_allclose(result, expected_result)

    data = [[[[0.1, 0.15], [0.15, 0.2]], [[0.05, 0.1], [-0.9, 0.05]]]]
    data_arguments = {"data": data, "attrs": {'reduce_by': ['y']}}
    expected_data = [[[0.05, 0.1], [-0.9, 0.05]]]
    expected_result = generate_data(data=expected_data, dims=('t','x','band'), attrs={'reduce_by': ['y']})
    result = execute_min_process(data_arguments)

    xr.testing.assert_allclose(result, expected_result)




