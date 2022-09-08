"""
Functions to prepare input for `pywapor.se_root`, more specifically to
interpolate various parameters in time to match with land-surface-temperature
times. 
"""

from pywapor.general.processing_functions import save_ds, open_ds, remove_ds
from pywapor.general.reproject import align_pixels
from pywapor.enhancers.apply_enhancers import apply_enhancer
from pywapor.general.logger import log
import os
import numpy as np
import xarray as xr
from itertools import chain


def is_aligned(ds, example_ds):
    return ds.equals(example_ds)


def main(dss, sources, example_source, folder, enhancers, example_t_vars = ["lst"]):
    """Aligns the datetimes in de `dss` xr.Datasets with the datetimes of the 
    dataset with variable `example_t_var`.

    Parameters
    ----------
    dss : dict
        Keys are tuples of (`source`, `product_name`), values are xr.Dataset's 
        or paths (str) to netcdf files, which will be aligned along the time dimensions.
    sources : dict
        Configuration for each variable and source.
    example_source : tuple, optional
        Which source to use for spatial alignment, overrides product selected
        through sources, by default None.
    folder : str
        Path to folder in which to store (intermediate) data.
    enhancers : list | "default", optional
        Functions to apply to the xr.Dataset before creating the final
        output, by default "default".
    example_t_var : str, optional
        Which variable to align the other datasets to in the time dimension, by default "lst".

    Returns
    -------
    xr.Dataset
        Dataset in which all variables have been interpolated to the same times.
    """
    # Open unopened netcdf files.
    dss = {**{k: open_ds(v) for k, v in dss.items() if isinstance(v, str)}, 
            **{k:v for k,v in dss.items() if not isinstance(v, str)}}

    # Determine final output path.
    final_path = os.path.join(folder, "se_root_in.nc")

    # Make list to store intermediate datasets.
    dss2 = list()

    # Make inventory of all variables.
    variables = [x for x in np.unique(list(chain.from_iterable([ds.data_vars for ds in dss.values()]))).tolist() if x in sources.keys()]
    variables = example_t_vars + [x for x in variables if x not in example_t_vars]

    # Create variable to store times to interpolate to.
    example_time = None

    cleanup = list()

    # Loop over the variables
    for var in variables:

        config = sources[var]
        spatial_interp = config["spatial_interp"]
        temporal_interp = config["temporal_interp"]

        # Align pixels of different products for a single variable together.
        dss_part = [ds[[var]] for ds in dss.values() if var in ds.data_vars]
        dss1, temp_files1 = align_pixels(dss_part, folder, spatial_interp, fn_append = "_step1")
        cleanup.append(temp_files1)

        # Combine different source_products (along time dimension).
        ds = xr.combine_nested(dss1, concat_dim = "time").chunk({"time": -1}).sortby("time").squeeze()

        if var in example_t_vars:
            if isinstance(example_time, type(None)):
                example_time = ds["time"]
            else:
                example_time = xr.concat([example_time, ds["time"]], dim = "time").drop_duplicates("time").sortby("time")
            dss2.append(ds)
        elif "time" in ds[var].dims:
            lbl = f"Aligning times in `{var}` ({ds.time.size}) with `{'` and `'.join(example_t_vars)}` ({example_time.time.size}, {temporal_interp})."
            ds = ds.interpolate_na(dim = "time", method = temporal_interp).ffill("time").bfill("time")
            ds = ds.interp_like(example_time, method = temporal_interp)
            dst_path = os.path.join(folder, f"{var}_i.nc")
            ds = save_ds(ds, dst_path, encoding = "initiate", label = lbl)
            dss2.append(ds)
            cleanup.append([ds])
        else:
            # Add time-invariant data as is.
            dss2.append(ds)

    # Align all the variables together.
    example_ds = dss[example_source]
    spatial_interps = [sources[list(x.data_vars)[0]]["spatial_interp"] for x in dss2]
    dss3, temp_files3 = align_pixels(dss2, folder, spatial_interps, example_ds, fn_append = "_step2")
    cleanup.append(temp_files3)

    # Merge everything.
    ds = xr.merge(dss3)

    # Apply product specific functions.
    for func in enhancers:
        ds, label = apply_enhancer(ds, var, func)
        log.info(label)

    if os.path.isfile(final_path):
        final_path = final_path.replace(".nc", "_.nc")

    if ds.time.size == 0:
        log.warning("--> No valid data created (ds.time.size == 0).")
        return ds

    ds = save_ds(ds, final_path, encoding = "initiate",
                    label = f"Creating merged file `{os.path.split(final_path)[-1]}`.")

    for nc in list(chain.from_iterable(cleanup)):
        remove_ds(nc)

    return ds

# if __name__ == "__main__":

#     import numpy as np
#     import glob

#     dss = {
#         ("SENTINEL2", "S2MSI2A"): r"/Users/hmcoerver/Local/test_data/SENTINEL2/S2MSI2A.nc",
#         ("SENTINEL3", "SL_2_LST___"): r"/Users/hmcoerver/Local/test_data/SENTINEL3/SL_2_LST___.nc",
#         # ("VIIRSL1", "VNP02IMG"): r"/Users/hmcoerver/Local/test_data/VIIRSL1/VNP02IMG.nc",
#     }
#     example_source = ("SENTINEL2", "S2MSI2A")

#     sources = {
#             "ndvi": {"spatial_interp": "nearest", "temporal_interp": "linear"},
#             "lst": {"spatial_interp": "nearest", "temporal_interp": "linear"},
#             "bt": {"spatial_interp": "nearest", "temporal_interp": "linear"},
#                 }

#     # example_source = ("source1", "productX")
#     folder = r"/Users/hmcoerver/Local/test_data"
#     enhancers = list()
#     example_t_vars = ["lst"]

#     chunks = (1, 500, 500)

#     for fp in glob.glob(os.path.join(folder, "*.nc")):
#         os.remove(fp)

#     from pywapor.general.logger import log, adjust_logger
#     adjust_logger(True, folder, "INFO")

#     ds = main(dss, sources, example_source, folder, enhancers, example_t_vars = ["lst"])