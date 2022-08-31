import os
from pywapor.collect.protocol import cog
from pywapor.general.processing_functions import open_ds
import numpy as np

def default_vars(product_name, req_vars):
    variables = {
        'WaPOR2': {
                "Band1": [("lat", "lon"), "z_oro"],
                "Band2": [("lat", "lon"), "vpd_slope"],
                "Band3": [("lat", "lon"), "t_amp_year"],
                "Band4": [("lat", "lon"), "rn_offset"],
                "Band5": [("lat", "lon"), "r0_full"],
                "Band6": [("lat", "lon"), "r0_bare"],
                "Band7": [("lat", "lon"), "rs_min"],
                "Band8": [("lat", "lon"), "rn_slope"],
                "Band9": [("lat", "lon"), "t_opt"],
                "Band10": [("lat", "lon"), "lw_slope"],
                "Band11": [("lat", "lon"), "land_mask"],
                "Band12": [("lat", "lon"), "lw_offset"],
                "Band13": [("lat", "lon"), "z_obst_max"],
                "crs": [(), "spatial_ref"],
                    },
        'WaPOR3': {
                "Band1": [("lat", "lon"), "lw_offset"],
                "Band2": [("lat", "lon"), "lw_slope"],
                "crs": [(), "spatial_ref"],
        }
    }

    req_dl_vars = {
        "WaPOR2": {
            "z_oro": ["Band1", "crs"],
            "vpd_slope": ["Band2", "crs"],
            "t_amp_year": ["Band3", "crs"],
            "rn_offset": ["Band4", "crs"],
            "r0_full": ["Band5", "crs"],
            "r0_bare": ["Band6", "crs"],
            "rs_min": ["Band7", "crs"],
            "rn_slope": ["Band8", "crs"],
            "t_opt": ["Band9", "crs"],
            "lw_slope": ["Band10", "crs"],
            "land_mask": ["Band11", "crs"],
            "lw_offset": ["Band12", "crs"],
            "z_obst_max": ["Band13", "crs"],
        },
        "WaPOR3": {
            "lw_offset": ["Band1", "crs"],
            "lw_slope": ["Band2", "crs"],
        },
    }

    out = {val:variables[product_name][val] for sublist in map(req_dl_vars[product_name].get, req_vars) for val in sublist}
    
    return out

def scale_factor(ds, var, scale = 0.01):
    ds[var] = ds[var] * scale
    return ds

def default_post_processors(product_name, req_vars):
    post_processors = {
        'WaPOR2': {
                    "land_mask": [],
                    "lw_offset": [],
                    "lw_slope": [],
                    "r0_bare": [],
                    "r0_full": [],
                    "rn_offset": [],
                    "rn_slope": [],
                    "rs_min": [],
                    "t_amp_year": [],
                    "t_opt": [],
                    "vpd_slope": [],
                    "z_obst_max": [],
                    "z_oro": [],
                    },
        'WaPOR3': {
                    "lw_offset": [],
                    "lw_slope": [],
                    },
    }

    out = {k:v for k,v in post_processors[product_name].items() if k in req_vars}

    return out

def url_func(product_name):
    url = f"https://storage.googleapis.com/fao-cog-data/{product_name}.tif"
    return url

def download(folder, latlim, lonlim, product_name, req_vars,
                variables = None, post_processors = None, **kwargs):
    
    folder = os.path.join(folder, "STATICS")
    
    fp = os.path.join(folder, f"{product_name}.nc")
    if os.path.isfile(fp):
        ds = open_ds(fp)
        if np.all([x in ds.data_vars for x in req_vars]):
            return ds
        else:
            ds = ds.close()

    spatial_buffer = True
    if spatial_buffer:
        dx = dy = 0.05
        latlim = [latlim[0] - dy, latlim[1] + dy]
        lonlim = [lonlim[0] - dx, lonlim[1] + dx]

    coords = {"x": ("lon", lonlim), "y": ("lat", latlim)}

    if isinstance(variables, type(None)):
        variables = default_vars(product_name, req_vars)

    if isinstance(post_processors, type(None)):
        post_processors = default_post_processors(product_name, req_vars)
    else:
        default_processors = default_post_processors(product_name, req_vars)
        post_processors = {k: {True: default_processors[k], False: v}[v == "default"] for k,v in post_processors.items()}

    ds = cog.download(fp, product_name, coords, variables, 
                        post_processors, url_func)
    
    return ds

if __name__ == "__main__":

    req_vars = [
                'land_mask',
                # 'lw_offset',
                'lw_slope',
                # 'r0_bare',
                'r0_full',
                'rn_offset',
                'rn_slope',
                'rs_min',
                't_amp_year',
                't_opt',
                # 'vpd_slope',
                'z_obst_max',
                'z_oro'
                ]

    product_name = "WaPOR2"

    folder = r"/Users/hmcoerver/Local/statics_test4"
    latlim = [28.9, 29.7]
    lonlim = [30.2, 31.2]

    ds = download(folder, latlim, lonlim, product_name, req_vars,
                variables = None, post_processors = None)
