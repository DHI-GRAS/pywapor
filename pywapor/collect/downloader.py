from pywapor.general.logger import log, adjust_logger
import types
import functools
import numpy as np

def collect_sources(folder, sources, latlim, lonlim, timelim, return_fps = True):
    """Download different sources and products within defined limits.

    Parameters
    ----------
    folder : str
        Path to folder in which to store files.
    sources : dict
        Configuration for each variable and source.
    latlim : list
        Latitude limits of area of interest.
    lonlim : list
        Longitude limits of area of interest.
    timelim : list
        Period for which to prepare data.
    return_fps : bool, optional
        Whether to return the datasets opened or closed as filepaths, by default True

    Returns
    -------
    tuple
        dictionary with keys as (`source`, `product`) and values either filepaths or `xr.Dataset`s and an
        updated `sources` dictionary in which products that couldn't be downloaded have been removed. 
    """
    
    reversed_sources, reversed_enhancers = reverse_sources(sources)

    dss = dict()

    max_attempts = 2
    attempts = {k: 0 for k in reversed_sources.keys()}

    while not np.all([v >= max_attempts for v in attempts.values()]):

        reversed_sources = {k: v for k, v in reversed_sources.items() if attempts[k] < max_attempts}

        for (source, product_name), req_vars in reversed_sources.items():
            
            if isinstance(source, str):
                dl_module = __import__(f"pywapor.collect.product.{source}", 
                                    fromlist=[source])
                dler = dl_module.download
                source_name = source
            elif isinstance(source, types.FunctionType):
                dler = source
                source_name = source.__name__
            elif isinstance(source, functools.partial):
                dler = source
                source_name = source.func.__name__

            log.info(f"--> Collecting `{'`, `'.join(req_vars)}` from `{source_name}.{product_name}`.")
            log.push().add()
            
            args = {
                "folder": folder,
                "latlim": latlim,
                "lonlim": lonlim,
                "timelim": timelim,
                "product_name": product_name,
                "req_vars": req_vars,
                "post_processors": reversed_enhancers[(source, product_name)]
            }

            try:
                x = dler(**args)
                attempts[(source, product_name)] += max_attempts * 10
            except Exception as e:

                if "NetCDF: Filter error: unimplemented filter encountered" in e.args[0]:
                    info_url = r"https://github.com/Unidata/netcdf4-python/issues/1182"
                    log.warning(f"--> Looks like you installed `netcdf4` incorrectly, see {info_url} for more info.")

                if attempts[(source, product_name)] < max_attempts - 1:
                    log.warning(f"--> Collect attempt {attempts[(source, product_name)] + 1} of {max_attempts} for `{source_name}.{product_name}` failed, trying again after other sources have been collected. ({type(e).__name__}: {e}).")
                else:
                    log.warning(f"--> Collect attempt {attempts[(source, product_name)] + 1} of {max_attempts} for `{source_name}.{product_name}` failed, giving up now, see full traceback below for more info. ({type(e).__name__}: {e}).")
                    log.exception("")

                attempts[(source, product_name)] += 1
            else:
                if "time" in x.coords:
                    stime = np.datetime_as_string(x.time.values[0], unit = "m")
                    etime = np.datetime_as_string(x.time.values[-1], unit = "m")
                    log.add().info(f"> timesize: {x.time.size} [{stime}, ..., {etime}]").sub()
                dss[(source_name, product_name)] = x
            finally:
                log.pop()
                continue

    if return_fps:
        for key, ds in dss.items():
            fp = ds.encoding["source"]
            ds = ds.close()
            dss[key] = fp

    reversed_sources = {k: v for k, v in reversed_sources.items() if attempts[k] <= max_attempts}
    sources = trim_sources(reversed_sources, sources)

    return dss, sources

def reverse_sources(sources):
    """Invert the `sources` so that the keys are like (`source`, `product`) and the values lists of variables.

    Parameters
    ----------
    sources : dict
        Configuration for each variable and source.

    Returns
    -------
    tuple
        the reversed sources dictionary and a dictionary listing the enhancers per (`source`, `product`).
    """
    reversed_sources = dict()
    reversed_enhancers = dict()
    for var, value in sources.items():
        for src in value["products"]:
            key = (src["source"], src["product_name"])
            enhancers = src["enhancers"]

            if key in reversed_sources.keys():
                reversed_sources[key].append(var)
                reversed_enhancers[key][var] = enhancers
            else:
                reversed_sources[key] = [var]
                reversed_enhancers[key] = {var: enhancers}

    return reversed_sources, reversed_enhancers

def trim_sources(reversed_sources, sources):
    """Remove (`source`, `product`)s from `sources` that couldn't be downloaded succesfully.

    Parameters
    ----------
    reversed_sources : dict
        Reversed sources dictionary
    sources : dict
        Configuration for each variable and source.

    Returns
    -------
    dict
        Configuration for each variable and source, where some have been removed.

    Raises
    ------
    ValueError
        Each `var` must contain unique `source.product`s.
    """
    for product, varis in reversed_sources.items():
        for var in varis:
            products_for_var = sources[var]["products"]
            idxs = [i for i, prod in enumerate(products_for_var) if (prod["source"], prod["product_name"]) == product]
            if len(idxs) == 0:
                continue
            elif len(idxs) == 1:
                removed_prod = sources[var]["products"].pop(idxs[0])
                log.warning(f"--> Continuing run without `{var}` from `{removed_prod['product_name']}`.")
            else:
                raise ValueError("Multiple identical `source.product`s for one var cannot exist")
        for var in varis:
            products_for_var = sources[var]["products"]
            if len(products_for_var) == 0:
                _ = sources.pop(var)
                log.warning(f"--> Continuing run without `{var}`, couldn't collect any product.")
    return sources

if __name__ == "__main__":

    return_fps = False

#     import datetime

#     sources = {

#         "r0":           {"products": [{"source": "MODIS", "product_name": "MCD43A3.061", "enhancers": "default"}]},
#         "z":            {"products": [{"source": "SRTM", "product_name": "30M", "enhancers": "default"}]},
#         "p":            {"products": [{"source": "CHIRPS", "product_name": "P05", "enhancers": "default"}]},
#         "lw_offset":    {"products": [{"source": "STATICS", "product_name": "WaPOR2", "enhancers": "default"}]},
#     }

#     folder = r"/Users/hmcoerver/Local/supersafe_dler"
#     latlim = [28.9, 29.7]
#     lonlim = [30.2, 31.2]
#     timelim = [datetime.date(2020, 7, 1), datetime.date(2020, 7, 15)]

#     adjust_logger(True, folder, "INFO")

#     dss0 = collect_sources(folder, sources, latlim, lonlim, timelim)
