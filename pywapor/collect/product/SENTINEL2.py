import glob
import os
import xarray as xr
import numpy as np
from datetime import datetime as dt
from pywapor.general.logger import log, adjust_logger
import pywapor.collect.protocol.sentinelapi as sentinelapi
import numpy as np
from functools import partial
from pywapor.general.processing_functions import open_ds, remove_ds

def apply_qa(ds, var):
    # 0 SC_NODATA # 1 SC_SATURATED_DEFECTIVE # 2 SC_DARK_FEATURE_SHADOW
    # 3 SC_CLOUD_SHADOW # 4 SC_VEGETATION # 5 SC_NOT_VEGETATED
    # 6 SC_WATER # 7 SC_UNCLASSIFIED # 8 SC_CLOUD_MEDIUM_PROBA
    # 9 SC_CLOUD_HIGH_PROBA # 10 SC_THIN_CIRRUS # 11 SC_SNOW_ICE
    if "qa" in ds.data_vars:
        pixel_qa_flags = [0, 1, 2, 3, 7, 8, 9, 10, 11]
        keep = np.invert(ds["qa"].isin(pixel_qa_flags))
        ds[var] = ds[var].where(keep)
    else:
        log.warning(f"--> Couldn't apply qa, since `qa` doesn't exist in this dataset ({list(ds.data_vars)}).")
    return ds

def mask_invalid(ds, var, valid_range = (1, 65534)):
    # 0 = NODATA, 65535 = SATURATED
    ds[var] = ds[var].where((ds[var] >= valid_range[0]) & (ds[var] <= valid_range[1]))
    return ds

def scale_data(ds, var):
    scale = 1./10000. # BOA_QUANTIFICATION_VALUE
    offset = -1000 # BOA_ADD_OFFSET
    ds[var] = (ds[var] + offset) * scale
    ds[var] = ds[var].where((ds[var] <= 1.00) & (ds[var] >= 0.00))
    return ds

def calc_normalized_difference(ds, var, bands = ["nir", "red"]):
    if np.all([x in ds.data_vars for x in bands]):
        ds[var] = xr.where(np.isclose(ds[bands[1]], 0), 0, (ds[bands[0]] - ds[bands[1]]) / (ds[bands[0]] + ds[bands[1]]))
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in bands if x not in ds.data_vars])}` is missing.")
    return ds

def calc_psri(ds, var):
    reqs = ["red", "blue", "red_edge_740"]
    if np.all([x in ds.data_vars for x in reqs]):
        ds[var] = xr.where(np.isclose(ds["red_edge_740"], 0), 0, (ds["red"] - ds["blue"]) / ds["red_edge_740"])
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in reqs if x not in ds.data_vars])}` is missing.")
    return ds

def calc_nmdi(ds, var):
    reqs = ["swir1", "swir2", "nir"]
    if np.all([x in ds.data_vars for x in reqs]):
        ds["nominator"] = ds["swir1"] - ds["swir2"]
        ds = calc_normalized_difference(ds, var, bands = ["nominator", "nir"])
        ds = ds.drop_vars(["nominator"])
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in reqs if x not in ds.data_vars])}` is missing.")
    return ds

def calc_bsi(ds, var):
    reqs = ["nir", "swir1", "red", "blue"]
    if np.all([x in ds.data_vars for x in reqs]):
        ds["nominator"] = ds["nir"] + ds["blue"]
        ds["denominator"] = ds["swir1"] + ds["red"]
        ds = calc_normalized_difference(ds, var, bands = ["nominator", "denominator"])
        ds = ds.drop_vars(["nominator", "denominator"])
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in reqs if x not in ds.data_vars])}` is missing.")
    return ds

def calc_vari_red_egde(ds, var):
    reqs = ["red_edge_740", "blue", "red"]
    if np.all([x in ds.data_vars for x in reqs]):
        n1 = ds["red_edge_740"] - 1.7 * ds["red"] + 0.7 * ds["blue"]
        n2 = ds["red_edge_740"] + 2.3 * ds["red"] - 1.3 * ds["blue"]
        ds[var] = xr.where(np.isclose(n2, 0), 0, n1 / n2)
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in reqs if x not in ds.data_vars])}` is missing.")
    return ds

def calc_r0(ds, var):
    weights = {
        "blue": 0.074,
        "green": 0.083,
        "red": 0.334,
        "nir": 0.356,
        "offset": 0.033,
    }
    reqs = ["blue", "green", "red", "nir"]
    if np.all([x in ds.data_vars for x in reqs]):
        ds["offset"] = xr.ones_like(ds["blue"])
        weights_da = xr.DataArray(data = list(weights.values()), 
                                coords = {"band": list(weights.keys())})
        ds["r0"] = ds[reqs + ["offset"]].to_array("band").weighted(weights_da).sum("band", skipna = False)
    else:
        log.warning(f"--> Couldn't calculate `{var}`, `{'` and `'.join([x for x in reqs if x not in ds.data_vars])}` is missing.")
    return ds

def default_vars(product_name, req_vars):

    variables = {
        "S2MSI2A": {
                    "_B02_20m.jp2": [(), "blue", [mask_invalid, apply_qa, scale_data]],
                    "_B03_20m.jp2": [(), "green", [mask_invalid, apply_qa, scale_data]],
                    "_B04_20m.jp2": [(), "red", [mask_invalid, apply_qa, scale_data]],
                    "_B05_20m.jp2": [(), "red_edge_703", [mask_invalid, apply_qa, scale_data]],
                    "_B06_20m.jp2": [(), "red_edge_740", [mask_invalid, apply_qa, scale_data]],
                    "_B07_20m.jp2": [(), "red_edge_782", [mask_invalid, apply_qa, scale_data]],
                    "_B8A_20m.jp2": [(), "nir", [mask_invalid, apply_qa, scale_data]],
                    "_B11_20m.jp2": [(), "swir1", [mask_invalid, apply_qa, scale_data]],
                    "_B12_20m.jp2": [(), "swir2", [mask_invalid, apply_qa, scale_data]],
                    "_SCL_20m.jp2": [(), "qa", []],
                },
    }

    req_dl_vars = {
        "S2MSI2A": {
            "blue":             ["_B02_20m.jp2", "_SCL_20m.jp2"],
            "green":            ["_B03_20m.jp2", "_SCL_20m.jp2"],
            "red":              ["_B04_20m.jp2", "_SCL_20m.jp2"],
            "red_edge_703":     ["_B05_20m.jp2", "_SCL_20m.jp2"],
            "red_edge_740":     ["_B06_20m.jp2", "_SCL_20m.jp2"],
            "red_edge_782":     ["_B07_20m.jp2", "_SCL_20m.jp2"],
            "nir":              ["_B8A_20m.jp2", "_SCL_20m.jp2"],
            "swir1":            ["_B11_20m.jp2", "_SCL_20m.jp2"],
            "swir2":            ["_B12_20m.jp2", "_SCL_20m.jp2"],
            "qa":               ["_SCL_20m.jp2"],
            "ndvi":             ["_B04_20m.jp2", "_B8A_20m.jp2", "_SCL_20m.jp2"],
            "mndwi":            ["_B03_20m.jp2", "_B11_20m.jp2", "_SCL_20m.jp2"],
            "vari_red_edge":    ["_B06_20m.jp2", "_B02_20m.jp2", "_B04_20m.jp2", "_SCL_20m.jp2"],
            "nmdi":             ["_B11_20m.jp2", "_B12_20m.jp2", "_B8A_20m.jp2", "_SCL_20m.jp2"],
            "psri":             ["_B02_20m.jp2", "_B04_20m.jp2", "_B06_20m.jp2", "_SCL_20m.jp2"],
            "bsi":              ["_B8A_20m.jp2", "_B11_20m.jp2", "_B04_20m.jp2", "_B02_20m.jp2", "_SCL_20m.jp2"],
            "r0":               ["_B02_20m.jp2", "_B03_20m.jp2", "_B04_20m.jp2", "_B8A_20m.jp2", "_SCL_20m.jp2"],
        },
    }

    out = {val:variables[product_name][val] for sublist in map(req_dl_vars[product_name].get, req_vars) for val in sublist}

    return out

def default_post_processors(product_name, req_vars):
    
    post_processors = {
        "S2MSI2A": {
            "blue":             [],
            "green":            [],
            "red":              [],
            "red_edge_703":     [],
            "red_edge_740":     [],
            "red_edge_782":     [],
            "nir":              [],
            "qa":               [],
            "swir1":            [],
            "swir2":            [],
            "psri":             [calc_psri],
            "ndvi":             [calc_normalized_difference],
            "nmdi":             [calc_nmdi],
            "vari_red_edge":    [calc_vari_red_egde],
            "bsi":              [calc_bsi],
            "mndwi":            [partial(calc_normalized_difference, bands = ["swir1", "green"])],
            "r0":               [calc_r0],
            },
    }

    out = {k:v for k,v in post_processors[product_name].items() if k in req_vars}

    return out

def time_func(fn):
    dtime = np.datetime64(dt.strptime(fn.split("_")[2], "%Y%m%dT%H%M%S"))
    return dtime

def s2_processor(scene_folder, variables):
    dss = [open_ds(glob.glob(os.path.join(scene_folder, "**", "*" + k), recursive = True)[0], decode_coords=None).isel(band=0).rename({"band_data": v[1]}) for k, v in variables.items()]
    ds = xr.merge(dss).drop_vars("band")
    return ds

def download(folder, latlim, lonlim, timelim, product_name, 
                req_vars, variables = None, post_processors = None, 
                extra_search_kwargs = {"cloudcoverpercentage": (0, 30)}):

    product_folder = os.path.join(folder, "SENTINEL2")

    fn = os.path.join(product_folder, f"{product_name}.nc")
    if os.path.isfile(fn):
        ds = open_ds(fn)
        if np.all([x in ds.data_vars for x in req_vars]):
            return ds
        else:
            remove_ds(ds)

    if isinstance(variables, type(None)):
        variables = default_vars(product_name, req_vars)

    if isinstance(post_processors, type(None)):
        post_processors = default_post_processors(product_name, req_vars)
    else:
        default_processors = default_post_processors(product_name, req_vars)
        post_processors = {k: {True: default_processors[k], False: v}[v == "default"] for k,v in post_processors.items()}

    if isinstance(timelim[0], str):
        timelim[0] = dt.strptime(timelim[0], "%Y-%m-%d")
        timelim[1] = dt.strptime(timelim[1], "%Y-%m-%d")

    bb = [lonlim[0], latlim[0], lonlim[1], latlim[1]]

    search_kwargs = {
                        "platformname": "Sentinel-2",
                        "producttype": product_name,
                        # "limit": 10,
    }

    search_kwargs = {**search_kwargs, **extra_search_kwargs}

    def node_filter(node_info):
        fn = os.path.split(node_info["node_path"])[-1]
        to_dl = list(variables.keys())
        return np.any([x in fn for x in to_dl])

    scenes = sentinelapi.download(product_folder, latlim, lonlim, timelim, search_kwargs, node_filter = node_filter)

    ds = sentinelapi.process_sentinel(scenes, variables, "SENTINEL2", time_func, f"{product_name}.nc", post_processors, bb = bb)

    return ds

if __name__ == "__main__":

    folder = r"/Users/hmcoerver/Local/s2_test"
    adjust_logger(True, folder, "INFO")
    timelim = ["2022-03-25", "2022-04-15"]
    latlim = [29.4, 29.7]
    lonlim = [30.7, 31.0]

    product_name = 'S2MSI2A'
    req_vars = ["mndwi"]
    post_processors = None
    variables = None
    extra_search_kwargs = {"cloudcoverpercentage": (0, 30)}

    ds = download(folder, latlim, lonlim, timelim, product_name, req_vars, 
                variables = None,  post_processors = None,
                extra_search_kwargs = extra_search_kwargs
                 )
