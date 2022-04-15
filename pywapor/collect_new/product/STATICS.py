import os
from pywapor.collect_new.protocol import cog

def default_vars(product_name, req_vars):
    variables = {
        'land_mask': {
                "Band1": [("lat", "lon"), "land_mask"],
                "crs": [(), "spatial_ref"],
                    },
        'lw_offset': {
                "Band1": [("lat", "lon"), "lw_offset"],
                "crs": [(), "spatial_ref"],
                    },
        'lw_slope': {
                "Band1": [("lat", "lon"), "lw_slope"],
                "crs": [(), "spatial_ref"],
                    },
        'r0_bare': {
                "Band1": [("lat", "lon"), "r0_bare"],
                "crs": [(), "spatial_ref"],
                    },
        'r0_full': {
                "Band1": [("lat", "lon"), "r0_full"],
                "crs": [(), "spatial_ref"],
                    },
        'rn_offset': {
                "Band1": [("lat", "lon"), "rn_offset"],
                "crs": [(), "spatial_ref"],
                    },
        'rn_slope': {
                "Band1": [("lat", "lon"), "rn_slope"],
                "crs": [(), "spatial_ref"],
                    },
        'rs_min': {
                "Band1": [("lat", "lon"), "rs_min"],
                "crs": [(), "spatial_ref"],
                    },
        't_amp_year': {
                "Band1": [("lat", "lon"), "t_amp_year"],
                "crs": [(), "spatial_ref"],
                    },
        't_opt': {
                "Band1": [("lat", "lon"), "t_opt"],
                "crs": [(), "spatial_ref"],
                    },
        'vpd_slope': {
                "Band1": [("lat", "lon"), "vpd_slope"],
                "crs": [(), "spatial_ref"],
                    },
        'z_obst_max': {
                "Band1": [("lat", "lon"), "z_obst_max"],
                "crs": [(), "spatial_ref"],
                    },
        'z_oro': {
                "Band1": [("lat", "lon"), "z_oro"],
                "crs": [(), "spatial_ref"],
                    },
    }

    req_dl_vars = {
        "land_mask": {
            "land_mask": ["Band1", "crs"],
        },
        "lw_offset": {
            "lw_offset": ["Band1", "crs"],
        },
        "lw_slope": {
            "lw_slope": ["Band1", "crs"],
        },
        "r0_bare": {
            "r0_bare": ["Band1", "crs"],
        },
        "r0_full": {
            "r0_full": ["Band1", "crs"],
        },
        "rn_offset": {
            "rn_offset": ["Band1", "crs"],
        },
        "rn_slope": {
            "rn_slope": ["Band1", "crs"],
        },
        "rs_min": {
            "rs_min": ["Band1", "crs"],
        },
        "t_amp_year": {
            "t_amp_year": ["Band1", "crs"],
        },
        "t_opt": {
            "t_opt": ["Band1", "crs"],
        },
        "vpd_slope": {
            "vpd_slope": ["Band1", "crs"],
        },
        "z_obst_max": {
            "z_obst_max": ["Band1", "crs"],
        },
        "z_oro": {
            "z_oro": ["Band1", "crs"],
        },
    }

    out = {val:variables[product_name][val] for sublist in map(req_dl_vars[product_name].get, req_vars) for val in sublist}
    
    return out

def default_post_processors(product_name, req_vars):
    post_processors = {
        'land_mask': {"land_mask": []},
        'lw_offset': {"lw_offset": []},
        'lw_slope': {"lw_slope": []},
        'r0_bare': {"r0_bare": []},
        'r0_full': {"r0_full": []},
        'rn_offset': {"rn_offset": []},
        'rn_slope': {"rn_slope": []},
        'rs_min': {"rs_min": []},
        't_amp_year': {"t_amp_year": []},
        't_opt': {"t_opt": []},
        'vpd_slope': {"vpd_slope": []},
        'z_obst_max': {"z_obst_max": []},
        'z_oro': {"z_oro": []},
    }

    out = [val for key, sublist in post_processors[product_name].items() for val in sublist if key in req_vars]
    if "_" in post_processors[product_name].keys():
        out += post_processors[product_name]["_"]

    return out

def url_func(product_name):
    base_url = r"https://storage.googleapis.com/fao-cog-data"
    url = os.path.join(base_url, f"L1_{product_name}.cog.tif")
    return url

def download(folder, latlim, lonlim, product_name, req_vars,
                variables = None, post_processors = None, **kwargs):
    
    folder = os.path.join(folder, "STATICS")
    
    coords = {"x": ("lon", lonlim), "y": ("lat", latlim)}

    if isinstance(variables, type(None)):
        variables = default_vars(product_name, req_vars)

    if isinstance(post_processors, type(None)):
        post_processors = default_post_processors(product_name, req_vars)

    ds = cog.download(folder, product_name, coords, variables, 
                        post_processors, url_func)
    
    return ds

if __name__ == "__main__":

    products = [
                'land_mask',
                'lw_offset',
                'lw_slope',
                'r0_bare',
                'r0_full',
                'rn_offset',
                'rn_slope',
                'rs_min',
                't_amp_year',
                't_opt',
                'vpd_slope',
                'z_obst_max',
                'z_oro'
                ]

    folder = r"/Users/hmcoerver/Downloads/pywapor_test"
    # latlim = [26.9, 33.7]
    # lonlim = [25.2, 37.2]
    latlim = [28.9, 29.7]
    lonlim = [30.2, 31.2]

    for product_name in products:
        ds = download(folder, latlim, lonlim, product_name, [product_name],
                    variables = None, post_processors = None)
