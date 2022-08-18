import os
from dask.diagnostics import ProgressBar
import numpy as np
from pywapor.general.logger import log
import xarray as xr
import numpy as np
import shutil
import glob
import warnings
import rasterio.warp
import pandas as pd
from pywapor.general.performance import performance_check

def process_ds(ds, coords, variables, crs = None):

    ds = ds[list(variables.keys())]

    ds = ds.rename({v[0]:k for k,v in coords.items() if k in ["x", "y"]})
    ds = ds.rename({k: v[1] for k, v in variables.items()})

    if not isinstance(crs, type(None)):
        ds = ds.rio.write_crs(crs)

    ds = ds.rio.write_grid_mapping("spatial_ref")

    for var in [x for x in list(ds.variables) if x not in ds.coords]:
        if "grid_mapping" in ds[var].attrs.keys():
            del ds[var].attrs["grid_mapping"]

    ds = ds.sortby("y", ascending = False)
    ds = ds.sortby("x")

    ds.attrs = {}

    return ds

def make_example_ds(folder, target_crs):
    example_ds_fp = os.path.join(folder, "example_ds.nc")
    if os.path.isfile(example_ds_fp):
        example_ds = open_ds(example_ds_fp)
    else:
        if not isinstance(bb, type(None)):
            if ds.rio.crs != target_crs:
                bb = transform_bb(target_crs, ds.rio.crs, bb)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category = FutureWarning)
                ds = ds.rio.clip_box(*bb)
            ds = ds.rio.pad_box(*bb)
        ds = ds.rio.reproject(target_crs)
        example_ds = save_ds(ds, example_ds_fp, label = f"Creating example dataset.") # NOTE saving because otherwise rio.reproject bugs.
    return example_ds

@performance_check
def save_ds(ds, fp, decode_coords = "all", encoding = None, chunks = "auto", precision = 2):
    """Save a `xr.Dataset` as netcdf.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset to save.
    fp : str
        Path to file to create.
    decode_coords : str, optional
        Controls which variables are set as coordinate variables when
        reopening the dataset, by default None.

    Returns
    -------
    xr.Dataset
        The newly created dataset.
    """
    temp_fp = fp.replace(".nc", "_temp.xx")

    folder = os.path.split(fp)[0]
    if not os.path.isdir(folder):
        os.makedirs(folder)

    if isinstance(chunks, dict):
        chunks = {dim: v for dim, v in chunks.items() if dim in ds.dims}

    ds = ds.chunk(chunks)

    if encoding == "initiate":
        if not isinstance(precision, dict):
            precision = {var: precision for var in ds.data_vars}
        encoding = {var: {
                        "zlib": True,
                        "_FillValue": -9999,
                        "chunksizes": tuple([v[0] for _, v in ds[var].chunksizes.items()]),
                        "dtype": "int32", # determine_dtype(ds[var], -9999, precision.get(var)),
                        "scale_factor": 10**-precision.get(var, 0), 
                        } for var in ds.data_vars}
        if "spatial_ref" in ds.coords:
            for var in ds.data_vars:
                if np.all([spat in ds[var].coords for spat in ["x", "y"]]):
                    ds[var].attrs.update({"grid_mapping": "spatial_ref"})
        for var in ds.coords:
            if var in ds.dims:
                encoding[var] = {"dtype": "float64"}

    with ProgressBar(minimum = 50, dt = 2.0):
        ds.to_netcdf(temp_fp, encoding = encoding)

    ds = ds.close()

    os.rename(temp_fp, fp)

    ds = open_ds(fp, decode_coords = decode_coords, chunks = chunks)

    return ds

def open_ds(fp, decode_coords = "all", chunks = "auto"):
    ds = xr.open_dataset(fp, decode_coords = decode_coords, chunks = chunks)
    return ds

def create_dummy_ds(varis, fp = None, shape = (10, 1000, 1000), chunks = (-1, 500, 500), sdate = "2022-02-01", edate = "2022-02-11", precision = 2, min_max = [-1, 1]):
    check = False
    if os.path.isfile(fp):
        os.remove(fp)
    if not check:
        nt, ny, nx = shape
        dates = pd.date_range(sdate, edate, periods = nt)
        ds = xr.Dataset({k: (["time", "y", "x"], np.random.uniform(size = np.prod(shape), low = min_max[0], high=min_max[1]).reshape(shape)) for k in varis}, coords = {"time": dates, "y": np.linspace(20, 30, ny), "x": np.linspace(40, 50, nx)})
        ds = ds.rio.write_crs(4326)
        if isinstance(chunks, tuple):
            chunks = {name: size for name, size in zip(["time", "y", "x"], chunks)}
        if not isinstance(fp, type(None)):
            ds = save_ds(ds, fp, chunks = chunks, encoding = "initiate", precision = precision, label = "Creating dummy dataset.")
    return ds

def determine_dtype(da, nodata, precision = None):
    if isinstance(precision, type(None)) and da.dtype.kind == "f":
        dtypes = [np.float16, np.float32, np.float64]
        precision = 0
        info = np.finfo
    else:
        dtypes = [np.int8, np.int16, np.int32, np.int64]
        info = np.iinfo
        if isinstance(precision, type(None)):
            precision = 0
    low = np.min([nodata, np.int0(np.floor(da.min().values * 10**precision))]) > [info(x).min for x in dtypes]
    high = np.max([nodata, np.int0(np.ceil(da.max().values * 10**precision))]) < [info(x).max for x in dtypes]
    check = np.all([low, high], axis = 0)
    if True in check:
        dtype = dtypes[np.argmax(check)]
    else:
        dtype = dtypes[-1]
        log.warning(f"--> Data for `{da.name}` with range [{np.int0(np.floor(da.min().values))}, {np.int0(np.ceil(da.max().values))}] doesnt fit inside dtype {dtype} with range [{np.iinfo(dtype).min}, {np.iinfo(dtype).max}] with a {precision} decimal precision.")
    return np.dtype(dtype).name

def create_wkt(latlim, lonlim):
    left = lonlim[0]
    bottom = latlim[0]
    right = lonlim[1]
    top = latlim[1]
    x = f"{left} {bottom},{right} {bottom},{right} {top},{right} {bottom},{left} {bottom}"
    return "GEOMETRYCOLLECTION(POLYGON((" + x + ")))"

def unpack(file, folder):
    fn = os.path.splitext(file)[0]
    shutil.unpack_archive(os.path.join(folder, file), folder)
    folder = [x for x in glob.glob(os.path.join(folder, fn + "*")) if os.path.isdir(x)][0]
    return folder

def transform_bb(src_crs, dst_crs, bb):
    bb =rasterio.warp.transform_bounds(src_crs, dst_crs, *bb, densify_pts=21)
    return bb

def calc_dlat_dlon(geo_out, size_X, size_Y, lat_lon = None):
    """
    Calculated the dimensions of each pixel in meter.

    Parameters
    ----------
    geo_out: list
        Geotransform function of the array.
    size_X: int
        Number of pixels in x-direction.
    size_Y: int
        Number of pixels in y-direction.

    Returns
    -------
    np.ndarray
        Size of every pixel in the y-direction in meters.
    dlon: array
        Size of every pixel in the x-direction in meters.
    """
    if isinstance(lat_lon, type(None)):
        # Create the lat/lon rasters
        lon = np.arange(size_X + 1)*geo_out[1]+geo_out[0] - 0.5 * geo_out[1]
        lat = np.arange(size_Y + 1)*geo_out[5]+geo_out[3] - 0.5 * geo_out[5]
    else:
        lat, lon = lat_lon

    dlat_2d = np.array([lat,]*int(np.size(lon,0))).transpose()
    dlon_2d =  np.array([lon,]*int(np.size(lat,0)))

    # Radius of the earth in meters
    R_earth = 6371000

    # Calculate the lat and lon in radians
    lonRad = dlon_2d * np.pi/180
    latRad = dlat_2d * np.pi/180

    # Calculate the difference in lat and lon
    lonRad_dif = abs(lonRad[:,1:] - lonRad[:,:-1])
    latRad_dif = abs(latRad[:-1] - latRad[1:])

    # Calculate the distance between the upper and lower pixel edge
    a = np.sin(latRad_dif[:,:-1]/2) * np.sin(latRad_dif[:,:-1]/2)
    clat = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    dlat = R_earth * clat

    # Calculate the distance between the eastern and western pixel edge
    b = np.cos(latRad[1:,:-1]) * np.cos(latRad[:-1,:-1]) * np.sin(lonRad_dif[:-1,:]/2) * np.sin(lonRad_dif[:-1,:]/2)
    clon = 2 * np.arctan2(np.sqrt(b), np.sqrt(1-b))
    dlon = R_earth * clon

    return(dlat, dlon)

if __name__ == "__main__":

    folder = r"/Users/hmcoerver/Local/dummy_ds_test"

    varis = ["my_var"]
    shape = (10, 1000, 1000)
    sdate = "2022-02-02"
    edate = "2022-02-13" 
    fp = os.path.join(folder, "dummy_test.nc")
    precision = 2
    min_max = [-1, 1]

    ds = create_dummy_ds(varis, 
                    shape = shape, 
                    sdate = sdate, 
                    edate = edate, 
                    fp = fp,
                    precision = precision,
                    min_max = min_max,
                    )