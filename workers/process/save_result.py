import os
from datetime import datetime, timedelta
from osgeo import gdal, osr
import boto3
import xarray as xr


from ._common import ProcessEOTask, StorageFailure, ProcessArgumentInvalid, ProcessArgumentRequired


S3_BUCKET_NAME = 'com.sinergise.openeo.results'
FAKE_AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
FAKE_AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


AWS_PRODUCTION = os.environ.get('AWS_PRODUCTION', '').lower() in ["true", "1", "yes"]
DATA_AWS_ACCESS_KEY_ID = os.environ.get('DATA_AWS_ACCESS_KEY_ID', FAKE_AWS_ACCESS_KEY_ID)
DATA_AWS_SECRET_ACCESS_KEY = os.environ.get('DATA_AWS_SECRET_ACCESS_KEY', FAKE_AWS_SECRET_ACCESS_KEY)
DATA_AWS_REGION = os.environ.get('DATA_AWS_REGION', 'eu-central-1')
DATA_AWS_S3_ENDPOINT_URL = os.environ.get('DATA_AWS_S3_ENDPOINT_URL', 'http://localhost:9000')


class save_resultEOTask(ProcessEOTask):
    _s3 = boto3.client('s3',
            region_name=DATA_AWS_REGION,
            aws_access_key_id=DATA_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=DATA_AWS_SECRET_ACCESS_KEY,
        ) if AWS_PRODUCTION else \
        boto3.client('s3',
            endpoint_url=DATA_AWS_S3_ENDPOINT_URL,
            region_name=DATA_AWS_REGION,
            aws_access_key_id=DATA_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=DATA_AWS_SECRET_ACCESS_KEY,
        )
    GDAL_DATATYPES = {
        'byte': gdal.GDT_Byte,
        'uint16': gdal.GDT_UInt16,
        'int16': gdal.GDT_Int16,
        'uint32': gdal.GDT_UInt32,
        'int32': gdal.GDT_Int32,
        'float32': gdal.GDT_Float32,
        'float64': gdal.GDT_Float64,
        'cint16': gdal.GDT_CInt16,
        'cint32': gdal.GDT_CInt32,
        'cfloat32': gdal.GDT_CFloat32,
        'cfloat64': gdal.GDT_CFloat64,
    }


    def _put_file_to_s3(self, filename, mime_type):
        object_key = '{}/{}'.format(self.job_id, os.path.basename(filename))
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object
        self._s3.put_object(
            ACL='private',  # https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl
            Body=open(filename, 'rb'),
            Bucket=S3_BUCKET_NAME,
            ContentType=mime_type,
            # https://aws.amazon.com/blogs/aws/amazon-s3-object-expiration/
            Expires=datetime.now() + timedelta(hours=1),
            Key=object_key,
        )

    @staticmethod
    def _clean_dir(dir_path):
        for filename in os.listdir(dir_path):
            os.unlink(os.path.join(dir_path, filename))
        os.rmdir(dir_path)

    def process(self, arguments):
        self.results = []

        try:
            data = arguments["data"]
        except:
            raise ProcessArgumentRequired("Process 'save_result' requires argument 'data'.")
        if not isinstance(data, xr.DataArray):
            raise ProcessArgumentInvalid("The argument 'data' in process 'save_result' is invalid: only cubes can be saved currently.")

        try:
            output_format = arguments['format'].lower()
        except:
            raise ProcessArgumentRequired("Process 'save_result' requires argument 'format'.")

        output_options = arguments.get('options', {})
        datatype = self.GDAL_DATATYPES.get(output_options.get('datatype', 'uint16').lower())

        if output_format != 'gtiff':
            raise ProcessArgumentInvalid("The argument 'format' in process 'save_result' is invalid: supported formats are: 'GTiff'.")
        for option in output_options:
            if option not in ['datatype']:
                raise ProcessArgumentInvalid("The argument 'options' in process 'save_result' is invalid, supported options are: 'datatype'.")
        if not datatype:
            raise ProcessArgumentInvalid("The argument 'options' in process 'save_result' is invalid: unknown value for option 'datatype'.")

        # https://stackoverflow.com/a/33950009
        tmp_job_dir = os.path.join("/tmp", self.job_id)
        os.mkdir(tmp_job_dir)

        bbox = data.attrs["bbox"]
        nx = len(data['x'])
        ny = len(data['y'])
        n_bands = len(data['band'])
        n_timestamps = len(data['t'])

        xmin, ymin = bbox.get_lower_left()
        xmax, ymax = bbox.get_upper_right()
        xres = (xmax - xmin) / float(nx)
        yres = (ymax - ymin) / float(ny)
        geotransform = (xmin, xres, 0, ymax, 0, -yres)

        for ti in range(n_timestamps):
            timestamp = data['t'].to_index()[0]
            t_str = timestamp.strftime('%Y-%m-%d_%H-%M-%S')

            filename = os.path.join(tmp_job_dir, "result-{}.tiff".format(t_str))

            # create the output file:
            dst_ds = gdal.GetDriverByName('GTiff').Create(filename, nx, ny, n_bands, datatype)

            dst_ds.SetGeoTransform(geotransform)    # specify coords
            srs = osr.SpatialReference()            # establish encoding
            srs.ImportFromEPSG(4326)                # EPSG:4326 by default
            dst_ds.SetProjection(srs.ExportToWkt()) # export coords to file
            for i in range(n_bands):
                band_data = data[{
                    "t": ti,
                    "band": i,
                }].values
                dst_ds.GetRasterBand(i + 1).WriteArray(band_data)   # write r-band to the raster

            dst_ds.FlushCache()                     # write to disk
            dst_ds = None

            try:
                self._put_file_to_s3(filename, 'image/tiff; application=geotiff')
            except Exception as ex:
                raise StorageFailure("Unable to store file(s).")

            self.results.append({
                'filename': os.path.basename(filename),
                'type': 'image/tiff; application=geotiff',
            })

        save_resultEOTask._clean_dir(tmp_job_dir)

        #print(result.to_series())
        # API requests that we return True / False:
        return True
