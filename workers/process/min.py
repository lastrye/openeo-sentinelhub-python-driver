import numpy as np
import xarray as xr

from ._common import ProcessEOTask, ProcessArgumentInvalid, ProcessArgumentRequired

class minEOTask(ProcessEOTask):
    """
        This process is often used within reduce process. Reduce could pass each of the vectors separately, 
        but this would be very inefficient. Instead, we get passed a whole xarray with an attribute reduce_by.
        In order to know, over which dimension should a callback process be applied, reduce appends the
        reduction dimension to the reduce_by attribute of the data. The last element of this list is the current
        reduction dimension. This also allows multi-level reduce calls.
    """
    def process(self, arguments):
        data = self.validate_parameter(arguments, "data", required=True, allowed_types=[xr.DataArray, list])
        ignore_nodata = self.validate_parameter(arguments, "ignore_nodata", default=True, allowed_types=[bool])

        original_type_was_number, data = self.convert_to_dataarray(data)

        if data.size == 0:
            return None

        dim = None
        if data.attrs and data.attrs.get("reduce_by"):
            dim = data.attrs.get("reduce_by")[-1]

        results = data.min(dim=dim, skipna=ignore_nodata, keep_attrs=True)
        return self.results_in_appropriate_type(results, original_type_was_number)

