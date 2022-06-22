# -*- coding: utf-8 -*-
"""
Code to run the SERoot model.
"""
import xarray as xr
import os
import numpy as np
import warnings
import pandas as pd
import datetime
import pywapor.general as g
import pywapor.general.processing_functions as PF
import pywapor.et_look_dev as ETLook_dev
import pywapor.et_look_v2 as ETLook_v2
from pywapor.general.logger import log, adjust_logger
from pywapor.general.processing_functions import save_ds, open_ds
import copy
import pywapor.pre_se_root as pre_se_root
from pywapor.general import levels

def se_root(folder, latlim, lonlim, timelim, sources = "level_1", bin_length = "DEKAD", **kwargs):
    if isinstance(sources, str):
        sources = levels.pre_se_root_levels(sources)
    ds_in = pre_se_root.main(folder, latlim, lonlim, timelim, sources, bin_length)
    ds_out = main(ds_in)
    return ds_out

def main(input_data, se_root_version = "v2", export_vars = "default"):
    """Runs the ETLook model over the provided input data.

    Parameters
    ----------
    input_data : str | xr.Dataset
        Dataset generated by `pywapor.pre_se_root`.
    se_root_version : "v2" | "dev", optional
        Which version of the SERoot model to use, by default "v2".
    export_vars : "default" | "all" | list, optional
        Specify which variables to save inside the output file. `"Default"` only 
        stores `se_root`. `"all"` stores all calculated variables. Use a
        list to specify a custom output set, by default "default".
    export_to_tif : bool, optional
        Return the variables selected with `export_vars` as netCDF (False) 
        or geoTIFF (True), by default False.

    Returns
    -------
    xr.Dataset | dict
        Returns a dataset or a dictionary with variable names as keys and
        lists with paths to geoTIFF files as values, depending on `export_to_tif`.
    """

    chunks = {"time": 1, "x": 2000, "y": 2000}

    # Inputs
    if isinstance(input_data, str):
        ds = open_ds(input_data, chunks = chunks)
    else:
        ds = input_data.chunk(chunks)
        input_data = ds.encoding["source"]

    _ = adjust_logger(True, os.path.split(input_data)[0], "INFO")

    t1 = datetime.datetime.now()
    log.info("> SE_ROOT").add()

    # Version
    if se_root_version == "v2":
        ETLook = ETLook_v2
    elif se_root_version == "dev":
        ETLook = ETLook_dev

    log.info(f"--> Running `se_root` ({se_root_version}).")

    warnings.filterwarnings("ignore", message="invalid value encountered in power")
    warnings.filterwarnings("ignore", message="invalid value encountered in log")

    # Allow skipping of et_look-functions if not all of its required inputs are
    # available.
    g.lazifier.decorate_submods(ETLook, g.lazifier.etlook_decorator)

    ds = g.variables.initiate_ds(ds)

    fp, fn = os.path.split(input_data)

    if se_root_version == "dev":
        ds["z0m_full"] = 0.04 + 0.01 * (ds.pixel_size - 30)/(250-30)
        ds["lst_zone_mean"] = lst_zone_mean(ds)

    if not ds["v2m_i"].dtype == object and not ds["u2m_i"].dtype == object:
        ds["u_i"] = np.sqrt(ds["v2m_i"]**2 + ds["u2m_i"]**2)

    doy = [int(pd.Timestamp(x).strftime("%j")) for x in ds["time"].values]
    ds["doy"] = xr.DataArray(doy, coords = ds["time"].coords).chunk("auto")
    dtime = [pd.Timestamp(x).hour + (pd.Timestamp(x).minute / 60) for x in ds["time"].values]
    ds["dtime"] = xr.DataArray(dtime, coords = ds["time"].coords).chunk("auto")
    ds["sc"] = ETLook.solar_radiation.seasonal_correction(ds["doy"])
    ds["decl"] = ETLook.solar_radiation.declination(ds["doy"])
    ds["day_angle"] = ETLook.clear_sky_radiation.day_angle(ds["doy"])

    if se_root_version == "dev":
        ds["t_air_i"] = xr.where(ds["t_air_i"] < -270, np.nan, ds["t_air_i"])

    ds["p_air_i"] = ETLook.meteo.air_pressure_kpa2mbar(ds["p_air_i"])
    ds["p_air_0_i"] = ETLook.meteo.air_pressure_kpa2mbar(ds["p_air_0_i"])

    ds["vc"] = ETLook.leaf.vegetation_cover(ds["ndvi"], nd_min = ds["nd_min"], nd_max = ds["nd_max"], vc_pow = ds["vc_pow"])

    ds["t_air_k_i"] = ETLook.meteo.air_temperature_kelvin_inst(ds["t_air_i"])
    ds["vp_i"] = ETLook.meteo.vapour_pressure_from_specific_humidity_inst(ds["qv_i"], ds["p_air_i"])
    ds["ad_moist_i"] = ETLook.meteo.moist_air_density_inst(ds["vp_i"], ds["t_air_k_i"])
    ds["ad_dry_i"] = ETLook.meteo.dry_air_density_inst(ds["p_air_i"], ds["vp_i"], ds["t_air_k_i"])
    ds["ad_i"] = ETLook.meteo.air_density_inst(ds["ad_dry_i"], ds["ad_moist_i"])
    ds["u_b_i_bare"] = ETLook.soil_moisture.wind_speed_blending_height_bare(ds["u_i"], z0m_bare = ds["z0m_bare"], z_obs = ds["z_obs"], z_b = ds["z_b"])
    ds["lon_rad"] = ETLook.solar_radiation.longitude_rad(ds["x"]).chunk("auto")
    ds["lat_rad"] = ETLook.solar_radiation.latitude_rad(ds["y"]).chunk("auto")
    ds["ha"] = ETLook.solar_radiation.hour_angle(ds["sc"], ds["dtime"], ds["lon_rad"])

    ds["ied"] = ETLook.clear_sky_radiation.inverse_earth_sun_distance(ds["day_angle"])
    ds["h0"] = ETLook.clear_sky_radiation.solar_elevation_angle(ds["lat_rad"], ds["decl"], ds["ha"])
    
    # ds["h0"] = ds["h0"].transpose("time", "y", "x").chunk("auto")
    
    ds["h0ref"] = ETLook.clear_sky_radiation.solar_elevation_angle_refracted(ds["h0"])
    ds["m"] = ETLook.clear_sky_radiation.relative_optical_airmass(ds["p_air_i"], ds["p_air_0_i"], ds["h0ref"])
    ds["rotm"] = ETLook.clear_sky_radiation.rayleigh_optical_thickness(ds["m"])
    ds["Tl2"] = ETLook.clear_sky_radiation.linke_turbidity(ds["wv_i"], ds["aod550_i"], ds["p_air_i"], ds["p_air_0_i"])
    ds["G0"] = ETLook.clear_sky_radiation.extraterrestrial_irradiance_normal(ds["IO"], ds["ied"])
    ds["B0c"] = ETLook.clear_sky_radiation.beam_irradiance_normal_clear(ds["G0"], ds["Tl2"], ds["m"], ds["rotm"], ds["h0"])
    ds["Bhc"] = ETLook.clear_sky_radiation.beam_irradiance_horizontal_clear(ds["B0c"], ds["h0"])
    ds["Dhc"] = ETLook.clear_sky_radiation.diffuse_irradiance_horizontal_clear(ds["G0"], ds["Tl2"], ds["h0"])

    ds["ra_hor_clear_i"] = ETLook.clear_sky_radiation.ra_clear_horizontal(ds["Bhc"], ds["Dhc"])
    ds["emiss_atm_i"] = ETLook.soil_moisture.atmospheric_emissivity_inst(ds["vp_i"], ds["t_air_k_i"])

    ds["rn_bare"] = ETLook.soil_moisture.net_radiation_bare(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["lst"], ds["r0_bare"])
    # ds["rn_bare"] = ds["rn_bare"].transpose("time", "y", "x").chunk("auto")

    ds["rn_full"] = ETLook.soil_moisture.net_radiation_full(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["lst"], ds["r0_full"])
    # ds["rn_full"] = ds["rn_full"].transpose("time", "y", "x").chunk("auto")

    ds["h_bare"] = ETLook.soil_moisture.sensible_heat_flux_bare(ds["rn_bare"], fraction_h_bare = ds["fraction_h_bare"])
    ds["h_full"] = ETLook.soil_moisture.sensible_heat_flux_full(ds["rn_full"], fraction_h_full = ds["fraction_h_full"])
    ds["u_b_i_full"] = ETLook.soil_moisture.wind_speed_blending_height_full_inst(ds["u_i"], z0m_full = ds["z0m_full"], z_obs = ds["z_obs"], z_b = ds["z_b"])

    ds["u_star_i_bare"] = ETLook.soil_moisture.friction_velocity_bare_inst(ds["u_b_i_bare"], z0m_bare = ds["z0m_bare"], disp_bare = ds["disp_bare"], z_b = ds["z_b"])
    ds["u_star_i_full"] = ETLook.soil_moisture.friction_velocity_full_inst(ds["u_b_i_full"], z0m_full = ds["z0m_full"], disp_full = ds["disp_full"], z_b = ds["z_b"])
    ds["L_bare"] = ETLook.soil_moisture.monin_obukhov_length_bare(ds["h_bare"], ds["ad_i"], ds["u_star_i_bare"], ds["t_air_k_i"])
    ds["L_full"] = ETLook.soil_moisture.monin_obukhov_length_full(ds["h_full"], ds["ad_i"], ds["u_star_i_full"], ds["t_air_k_i"])

    ds["u_i_soil"] = ETLook.soil_moisture.wind_speed_soil_inst(ds["u_i"], ds["L_bare"], z_obs = ds["z_obs"])
    ds["ras"] = ETLook.soil_moisture.aerodynamical_resistance_soil(ds["u_i_soil"])
    ds["raa"] = ETLook.soil_moisture.aerodynamical_resistance_bare(ds["u_i"], ds["L_bare"], z0m_bare = ds["z0m_bare"], disp_bare = ds["disp_bare"], z_obs = ds["z_obs"])
    ds["rac"] = ETLook.soil_moisture.aerodynamical_resistance_full(ds["u_i"], ds["L_full"], z0m_full = ds["z0m_full"], disp_full = ds["disp_full"], z_obs = ds["z_obs"])

    ds["t_max_bare"] = ETLook.soil_moisture.maximum_temperature_bare(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["ad_i"], ds["raa"], ds["ras"], ds["r0_bare"])
    ds["t_max_full"] = ETLook.soil_moisture.maximum_temperature_full(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["ad_i"], ds["rac"], ds["r0_full"])

    ds["t_wet_i"] = ETLook.soil_moisture.wet_bulb_temperature_inst_new(ds["t_air_i"], ds["qv_i"], ds["p_air_i"])
    ds["lst_max"] = ETLook.soil_moisture.maximum_temperature(ds["t_max_bare"], ds["t_max_full"], ds["vc"])

    if se_root_version == "v2":
        ds["t_wet_k_i"] = ETLook.meteo.wet_bulb_temperature_kelvin_inst(ds["t_wet_i"])
        ds["lst_min"] = ETLook.soil_moisture.minimum_temperature(ds["t_wet_k_i"], ds["t_air_k_i"], ds["vc"])
    elif se_root_version == "dev":
        ds["t_min_bare"] = ETLook.soil_moisture.minimum_temperature_bare(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["ad_i"], ds["raa"], ds["ras"], ds["lst_zone_mean"], r0_bare_wet = ds["r0_bare_wet"])
        ds["t_min_full"] = ETLook.soil_moisture.minimum_temperature_full(ds["ra_hor_clear_i"], ds["emiss_atm_i"], ds["t_air_k_i"], ds["ad_i"], ds["rac"], ds["lst_zone_mean"], ds["r0_full"])  
        ds["lst_min"] = ETLook.soil_moisture.maximum_temperature(ds["t_min_bare"], ds["t_min_full"], ds["vc"])

    ds["se_root"] = ETLook.soil_moisture.soil_moisture_from_maximum_temperature(ds["lst_max"], ds["lst"], ds["lst_min"])

    if export_vars == "all":
        ...
    elif export_vars == "default":
        keep_vars = ['se_root']
        ds = ds[keep_vars]
    elif isinstance(export_vars, list):
        keep_vars = copy.copy(export_vars)
        ds = ds[keep_vars]
    else:
        raise ValueError

    ds = g.variables.fill_attrs(ds)

    if len(ds.data_vars) == 0:
        log.info("--> No data to export, try adjusting `export_vars`.")
        ds = None
    else:
        fn = fn.replace("in", "out")
        fp_out = os.path.join(fp, fn)
        if os.path.isfile(fp_out):
            fp_out = fp_out.replace(".nc", "_.nc")
        ds = save_ds(ds, fp_out, decode_coords = "all", chunks = chunks)

    t2 = datetime.datetime.now()
    log.sub().info(f"< SE_ROOT ({str(t2 - t1)})")

    return ds

def lst_zone_mean(ds):
    # TODO This function needs to be replaced by something like pywapor.enhancers.temperature.local_mean

    geo_ex = ds.geotransform
    proj_ex = ds.projection

    size_y, size_x = ds["ndvi"].isel(time = 0).shape
    size_y_zone = int(np.ceil(size_y/200))
    size_x_zone = int(np.ceil(size_x/200)) 
    array_fake = np.ones([size_y_zone, size_x_zone])
    geo_new = tuple([geo_ex[0], geo_ex[1] * 200, geo_ex[2], geo_ex[3], geo_ex[4], geo_ex[5]*200])
    MEM_file = PF.Save_as_MEM(array_fake, geo_new, proj_ex)

    lst_zone_mean_full = np.ones_like(ds["ndvi"] * np.nan)

    for i, t in enumerate(ds.time):

        lst = ds["lst"].sel(time = t).values
        lst_filename = PF.Save_as_MEM(lst, geo_new, proj_ex)
        
        dest_lst_zone_large = PF.reproject_dataset_example(lst_filename, MEM_file, 4)
        lst_zone_mean_large = dest_lst_zone_large.GetRasterBand(1).ReadAsArray()
        lst_zone_mean_large[lst_zone_mean_large==0] = -9999
        lst_zone_mean_large[np.isnan(lst_zone_mean_large)] = -9999

        if np.nanmax(lst_zone_mean_large) == -9999:
            for x in range(0, size_x_zone):
                for y in range(0, size_y_zone):
                    lst_zone_mean_large[y, x] = np.nanmean(lst[y*200:np.minimum((y+1)*200, size_y-1), x*200:np.minimum((x+1)*200, size_x-1)])
            lst_zone_mean_large[np.isnan(lst_zone_mean_large)] = -9999

        lst_zone_mean_large = PF.gap_filling(lst_zone_mean_large, -9999, 1)
        dest_lst_zone_large = PF.Save_as_MEM(lst_zone_mean_large, geo_new, proj_ex)
        
        dest_lst_zone = PF.reproject_dataset_example(dest_lst_zone_large, lst_filename, 6)
        lst_zone_mean = dest_lst_zone.GetRasterBand(1).ReadAsArray()

        lst_zone_mean_full[i, ...] = lst_zone_mean
        
    lst_zone_mean_da = xr.DataArray(lst_zone_mean_full, coords = ds.ndvi.coords)

    return lst_zone_mean_da

def test_ds(ds, var):
    from dask.diagnostics import Profiler, ResourceProfiler, CacheProfiler, ProgressBar
    from dask.diagnostics import visualize

    with Profiler() as prof, ResourceProfiler(dt=0.25) as rprof, CacheProfiler() as cprof, ProgressBar():
        out = ds[var].compute()

    visualize([prof, rprof, cprof])
    return out

if __name__ == "__main__":

    se_root_version = "v2"
    export_vars = "default"
    export_to_tif = False

    from pywapor.general.processing_functions import open_ds
    import pywapor

    
    # input_data1 = r"/Users/hmcoerver/pywapor_notebooks_1/et_look_in.nc"
    # test = pywapor.et_look.main(input_data1)


    folder = r"/Users/hmcoerver/pywapor_notebooks_1"
    latlim = [28.9, 29.7]
    lonlim = [30.2, 31.2]
    timelim = [datetime.date(2021, 7, 1), datetime.date(2021, 7, 11)]
    bin_length = "DEKAD"
    example_source = None

    # input_data = pywapor.pre_se_root.main(folder, latlim, lonlim, timelim, "level_1", bin_length)
    input_data = xr.open_dataset(r"/Users/hmcoerver/pywapor_notebooks_2/se_root_in.nc", decode_coords="all", chunks = {"time": 1, "x": 2000, "y": 2000})
    
    # input_data = input_data[["qv_i", "p_air_i"]]

    out_ds = pywapor.se_root.main(input_data, export_vars = "all")

    # import dask
    # dask.config.set(**{'array.chunk-size': '10MiB'})
    # test = out_ds.chunk("auto")

    # fp = r"/Users/hmcoerver/Downloads/pywapor_test/test_1.nc"

    # bla = save_ds(test, fp, "all")
