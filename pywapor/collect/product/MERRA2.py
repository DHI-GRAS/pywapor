import datetime
import pandas as pd
import pywapor.collect.accounts as accounts
from pywapor.general.logger import log
from pywapor.collect.protocol.projections import get_crss
import pywapor.collect.protocol.opendap as opendap
import fnmatch
import os
from functools import partial
from pywapor.general.processing_functions import open_ds
from pywapor.collect.protocol.requests import find_paths
from pywapor.enhancers.temperature import kelvin_to_celsius

def default_vars(product_name, req_vars):
    variables = {
        "M2I1NXASM.5.12.4": {
                    "T2M": [("time", "lat", "lon"), "t_air"],
                    "U2M": [("time", "lat", "lon"), "u2m"],
                    "V2M": [("time", "lat", "lon"), "v2m"],
                    "QV2M": [("time", "lat", "lon"), "qv"],
                    "TQV": [("time", "lat", "lon"), "wv"],
                    "PS": [("time", "lat", "lon"), "p_air"],
                    "SLP": [("time", "lat", "lon"), "p_air_0"],
                        },
        "M2T1NXRAD.5.12.4": {
                    "SWGNT": [("time", "lat", "lon"), "ra"],
                        }
    }

    req_dl_vars = {
        "M2I1NXASM.5.12.4": {
            "t_air": ["T2M"],
            "t_air_max" :["T2M"],
            "t_air_min" :["T2M"],
            "u2m": ["U2M"],
            "v2m": ["V2M"],
            "qv": ["QV2M"],
            "wv": ["TQV"],
            "p_air": ["PS"],
            "p_air_0": ["SLP"],
        },
        "M2T1NXRAD.5.12.4": {
            "ra": ["SWGNT"],
        }
    }

    out = {val:variables[product_name][val] for sublist in map(req_dl_vars[product_name].get, req_vars) for val in sublist}
    
    return out

def pa_to_kpa(ds, var):
    ds[var] = ds[var] / 1000
    return ds

def default_post_processors(product_name, req_vars):
    post_processors = {
        "M2I1NXASM.5.12.4": {
            "t_air": [kelvin_to_celsius], 
            "t_air_max": [partial(kelvin_to_celsius, in_var = "t_air", out_var = "t_air_max")],
            "t_air_min": [partial(kelvin_to_celsius, in_var = "t_air", out_var = "t_air_min")],
            "u2m": [],
            "v2m": [],
            "qv": [],
            "wv": [],
            "p_air": [pa_to_kpa],
            "p_air_0": [pa_to_kpa],
        },
        "M2T1NXRAD.5.12.4": {
            "ra": [],
        },
    }

    out = {k:v for k,v in post_processors[product_name].items() if k in req_vars}

    return out

def fn_func(product_name, tile):
    fn = f"{product_name}_{tile.strftime('%Y%m%d')}.nc"
    return fn

def url_func(product_name, tile):

    def _filter(tag):
        tag_value = tag["href"]
        if tag_value[-5:] == ".html":
            tag_value = tag_value[:-5] 
        return tag_value
    # Find the existing tiles for the given year and month, this is necessary
    # because the version number (`\d{3}`) in the filenames is irregular.
    regex = r"MERRA2_\d{3}\..*\.\d{8}.nc4.html"
    url = f"https://goldsmr4.gesdisc.eosdis.nasa.gov/opendap/MERRA2/{product_name}/{tile.year}/{tile.month:02d}/contents.html"
    tile_names = find_paths(url, regex, filter = _filter)

    # Find which of the existing tiles matches with the date.
    fn_pattern = f"MERRA2_*.*.{tile.strftime('%Y%m%d')}.nc4"
    fn = fnmatch.filter(tile_names, fn_pattern)[0]

    # Create the final url.
    url = f"https://goldsmr4.gesdisc.eosdis.nasa.gov/opendap/MERRA2/{product_name}/{tile.year}/{tile.month:02d}/{fn}.nc4?"  
    return url

def download(folder, latlim, lonlim, timelim, product_name, req_vars,
                variables = None, post_processors = None):
    
    folder = os.path.join(folder, "MERRA2")
    fn = os.path.join(folder, f"{product_name}.nc")
    if os.path.isfile(fn):
        return open_ds(fn, "all")

    spatial_buffer = True
    if spatial_buffer:
        latlim = [latlim[0] - 0.5, latlim[1] + 0.5]
        lonlim = [lonlim[0] - 0.625, lonlim[1] + 0.625]

    tiles = pd.date_range(timelim[0], timelim[1], freq="D")
    coords = {"x": ["lon", lonlim], "y":["lat", latlim], "t": ["time", timelim]}
    if isinstance(variables, type(None)):
        variables = default_vars(product_name, req_vars)
    
    if isinstance(post_processors, type(None)):
        post_processors = default_post_processors(product_name, req_vars)
    else:
        default_processors = default_post_processors(product_name, req_vars)
        post_processors = {k: {True: default_processors[k], False: v}[v == "default"] for k,v in post_processors.items()}

    data_source_crs = get_crss("WGS84")
    parallel = True
    spatial_tiles = False
    un_pw = accounts.get("NASA")
    request_dims = True

    ds = opendap.download(folder, product_name, coords, 
                variables, post_processors, fn_func, url_func, un_pw = un_pw, 
                tiles = tiles, data_source_crs = data_source_crs, parallel = parallel, 
                spatial_tiles = spatial_tiles, request_dims = request_dims)
    return ds


if __name__ == "__main__":

    folder = r"/Users/hmcoerver/Downloads/pywapor_test"
    # latlim = [26.9, 33.7]
    # lonlim = [25.2, 37.2]
    latlim = [28.9, 29.7]
    lonlim = [30.2, 31.2]
    timelim = [datetime.date(2020, 7, 1), datetime.date(2020, 7, 11)]

    variables = None
    post_processors = None
    
    # # MERRA2.
    # wanted = [
    #             ("M2I1NXASM.5.12.4", ["t_air", "u2m", "v2m", "qv", "wv", "p_air", "p_air_0"]),
    #             # ("M2T1NXRAD.5.12.4", ["ra"]),
    #         ]

    product_name = "M2I1NXASM.5.12.4"
    req_vars = ["t_air", "u2m", "v2m", "qv", "wv", "p_air", "p_air_0"]

    # for product_name, req_vars in wanted:
    # ds = download(folder, latlim, lonlim, timelim, product_name, req_vars)
    # print(ds.rio.crs, ds.rio.grid_mapping)
