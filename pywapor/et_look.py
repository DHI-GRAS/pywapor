# -*- coding: utf-8 -*-
"""
Code to run the ETLook model.
"""
import os
import numpy as np
import pywapor.et_look_v2_v3 as ETLook_v2_v3
import pywapor.general as g
import datetime
from pywapor.general.logger import log, adjust_logger
from pywapor.general.processing_functions import save_ds, open_ds
import copy
import warnings

def main(input_data, et_look_version = "v2", export_vars = "default", chunks = {"time_bins": -1, "x": 500, "y": 500}):
    """Runs the ETLook model over the provided input data.

    Parameters
    ----------
    input_data : str | xr.Dataset
        Dataset generated by `pywapor.pre_et_look`.
    et_look_version : "v2" | "v3", optional
        Which version of the ETLook model to use, by default "v2".
    export_vars : "default" | "all" | list, optional
        Specify which variables to save inside the output file. `"Default"` stores `int_mm`,
        `t_24_mm`, `e_24_mm`, `aeti_24_mm`, `et_ref_24_mm`, `se_root`, `biomass_prod`,
        `epoch_ends` and `epoch_starts`. `"all"` stores all calculated variables. Use a
        list to specify a custom output set, by default "default".
    chunks : dict, optional
        Specify how the calculations are split up. Increase chunk sizes to speed up calculation,
        decrease to use less RAM, by default {"time": 1, "x": 1000, "y": 1000}.


    Returns
    -------
    xr.Dataset
        Dataset with variables selected through `export_vars`.
    """

    # Inputs
    if isinstance(input_data, str):
        ds = open_ds(input_data, chunks = chunks)
    else:
        ds = copy.deepcopy(input_data).chunk(chunks)
        input_data = ds.encoding["source"]

    _ = adjust_logger(True, os.path.split(input_data)[0], "INFO")

    t1 = datetime.datetime.now()
    log.info("> ET_LOOK").add()

    # Version
    ETLook = ETLook_v2_v3

    log.info(f"--> Running `et_look` ({et_look_version}).")

    # Allow skipping of et_look-functions if not all of its required inputs are
    # available.
    g.lazifier.decorate_submods(ETLook, g.lazifier.etlook_decorator)

    ds = g.variables.initiate_ds(ds)

    if ds["rs_min"].dtype == object:
        ds["rs_min"] = 100
        log.info(f"--> Setting `rs_min` to `100`.")

    if ds["land_mask"].dtype == object:
        ds["land_mask"] = 1
        log.info(f"--> Setting `land_mask` to `1`.")

    if ds["z_obst_max"].dtype == object:
        ds["z_obst_max"] = 3
        log.info(f"--> Setting `z_obst_max` to `3`.")

    ds["decl"] = ETLook.solar_radiation.declination(ds["doy"])
    ds["iesd"] = ETLook.solar_radiation.inverse_earth_sun_distance(ds["doy"])

    ds["z_obs"] = ds["lai"].copy(data = np.zeros(ds["lai"].shape) + 100)
    ds["z_b"] = ds["lai"].copy(data = np.zeros(ds["lai"].shape) + 100)

    ######################## MODEL ETLOOK ####################################

    # **effective_leaf_area_index*********************************************
    #ds["vc"] = ETLook.leaf.vegetation_cover(ds["ndvi"], nd_min = ds["nd_min"], nd_max = ds["nd_max"], vc_pow = ds["vc_pow"])
    #ds["lai"] = ETLook.leaf.leaf_area_index(ds["vc"], vc_min = ds["vc_min"], vc_max = ds["vc_max"], lai_pow = ds["lai_pow"])
    ds["lai_eff"] = ETLook.leaf.effective_leaf_area_index(ds["lai"])

    # *******TRANSPIRATION COMPONENT******************************************

    # **soil fraction*********************************************************
    ds["sf_soil"] = ETLook.radiation.soil_fraction(ds["lai"])

    # **atmospheric canopy resistance***********************************************
    ds["lat_rad"] = ETLook.solar_radiation.latitude_rad(ds["y"]).chunk("auto")
    ds["ws"] = ETLook.solar_radiation.sunset_hour_angle(ds["lat_rad"], ds["decl"])

    ds["ra_toa_flat_24"] = ETLook.solar_radiation.daily_solar_radiation_toa_flat(ds["decl"], ds["iesd"], ds["lat_rad"], ds["ws"])

    # ra_24 is already calculated
    ds["trans_24"] = ETLook.solar_radiation.transmissivity(ds["ra_flat_24"], ds["ra_toa_flat_24"])
    #if ds["slope"].dtype == object or ds["aspect"].dtype == object:
    #    ds["ra_24"] = ds["ra_flat_24"]
    #    ds["trans_24"] = ETLook.solar_radiation.transmissivity(ds["ra_flat_24"], ds["ra_toa_flat_24"])
    #else:
    #    ds["sc"] = ETLook.solar_radiation.seasonal_correction(ds["doy"])
    #    ds["ra_toa_24"] = ETLook.solar_radiation.daily_solar_radiation_toa(ds["sc"], ds["decl"], ds["iesd"], ds["lat_rad"], ds["slope"], ds["aspect"])
    #    ds["trans_24"] = ETLook.solar_radiation.transmissivity(ds["ra_flat_24"], ds["ra_toa_flat_24"])
    #    ds["diffusion_index"] = ETLook.solar_radiation.diffusion_index(ds["trans_24"], diffusion_slope = ds["diffusion_slope"], diffusion_intercept = ds["diffusion_intercept"])
    #    ds["ra_24"] = ETLook.solar_radiation.daily_total_solar_radiation(ds["ra_toa_24"], ds["ra_toa_flat_24"], ds["diffusion_index"], ds["trans_24"])

    ds["stress_rad"] = ETLook.stress.stress_radiation(ds["ra_24"])
    # p_air_24 is already in mbar and adjusted for elevation
    #ds["p_air_0_24_mbar"] = ETLook.meteo.air_pressure_kpa2mbar(ds["p_air_0_24"])
    #ds["p_air_24"] = ETLook.meteo.air_pressure_daily(ds["z"], ds["p_air_0_24_mbar"])

    # vp_24 is already calculated
    #if ds["vp_24"].dtype == object:
    #    ds["vp_24"] = ETLook.meteo.vapour_pressure_from_specific_humidity_daily(ds["qv_24"], ds["p_air_24"])
    #if ds["vp_24"].dtype == object:
    #    ds["vp_24"] = ETLook.meteo.vapour_pressure_from_dewpoint_daily(ds["t_dew_24"])

    if et_look_version == "v2":
        ds["svp_24"] = ETLook.meteo.saturated_vapour_pressure(ds["t_air_24"])
    else:
        ds["svp_24_min"] = ETLook.meteo.saturated_vapour_pressure_minimum(ds["t_air_min_24"])
        ds["svp_24_max"] = ETLook.meteo.saturated_vapour_pressure_maximum(ds["t_air_max_24"])
        ds["svp_24"] = ETLook.meteo.saturated_vapour_pressure_average(ds["svp_24_max"], ds["svp_24_min"])

    ds["vpd_24"] = ETLook.meteo.vapour_pressure_deficit_daily(ds["svp_24"], ds["vp_24"])
    ds["stress_vpd"] = ETLook.stress.stress_vpd(ds["vpd_24"], ds["vpd_slope"])
    #ds["stress_temp"] = ETLook.stress.stress_temperature(ds["t_air_24"], t_opt = ds["t_opt"], t_min = ds["t_min"], t_max = ds["t_max"])
    ds["stress_temp"] = ETLook.stress.stress_temperature(ds["t_air_24"], t_opt = ds["t_opt"])

    #ds["r_canopy_0"] = ETLook.resistance.atmospheric_canopy_resistance(ds["lai_eff"], ds["stress_rad"], ds["stress_vpd"], ds["stress_temp"], rs_min = ds["rs_min"], rcan_max = ds["rcan_max"])
    ds["r_canopy_0"] = ETLook.resistance.atmospheric_canopy_resistance(ds["lai_eff"], ds["stress_rad"], ds["stress_vpd"], ds["stress_temp"])

    # **net radiation canopy******************************************************
    ds["t_air_k_24"] = ETLook.meteo.air_temperature_kelvin_daily(ds["t_air_24"])
    #ds["l_net"] = ETLook.radiation.longwave_radiation_fao(ds["t_air_k_24"], ds["vp_24"], ds["trans_24"], vp_slope = ds["vp_slope"], vp_offset = ds["vp_offset"], lw_slope = ds["lw_slope"], lw_offset = ds["lw_offset"])
    ds["l_net"] = ETLook.radiation.longwave_radiation_fao(ds["t_air_k_24"], ds["vp_24"], ds["trans_24"], lw_slope = ds["lw_slope"], lw_offset = ds["lw_offset"])
    #ds["int_mm"] = ETLook.evapotranspiration.interception_mm(ds["p_24"], ds["vc"], ds["lai"], int_max = ds["int_max"])
    ds["int_mm"] = ETLook.evapotranspiration.interception_mm(ds["p_24"], ds["vc"], ds["lai"])
    ds["lh_24"] = ETLook.meteo.latent_heat_daily(ds["t_air_24"])
    ds["int_wm2"] = ETLook.radiation.interception_wm2(ds["int_mm"], ds["lh_24"])
    ds["rn_24"] = ETLook.radiation.net_radiation(ds["r0"], ds["ra_24"], ds["l_net"], ds["int_wm2"])
    ds["rn_24_canopy"] = ETLook.radiation.net_radiation_canopy(ds["rn_24"], ds["sf_soil"])

    #ds["stress_moist"] = ETLook.stress.stress_moisture(ds["se_root"], tenacity = ds["tenacity"])
    #ds["r_canopy"] = ETLook.resistance.canopy_resistance(ds["r_canopy_0"], ds["stress_moist"], rcan_max = ds["rcan_max"])
    ds["stress_moist"] = ETLook.stress.stress_moisture(ds["se_root"],)
    ds["r_canopy"] = ETLook.resistance.canopy_resistance(ds["r_canopy_0"], ds["stress_moist"])

    # **initial canopy aerodynamic resistance***********************************************************
    if ds["z_oro"].dtype == object: # TODO this function is wrong...
        ds["z_oro"] = 0.001
        log.info(f"--> Setting `z_oro` to `0.001`.")
        # ds["z_oro"] = ETLook.roughness.orographic_roughness(ds["z"], ds["x"], ds["y"])

    # z_obst is already calculated for herbaceous and tree vegetation
    #ds["z_obst"] = ETLook.roughness.obstacle_height(ds["ndvi"], ds["z_obst_max"], ndvi_obs_min = ds["ndvi_obs_min"], ndvi_obs_max = ds["ndvi_obs_max"], obs_fr = ds["obs_fr"])
    ds["z0m"] = ETLook.roughness.roughness_length(ds["lai"], ds["z_oro"], ds["z_obst"], ds["z_obst_max"], ds["land_mask"])
    if ds["u_24"].dtype == object:
        ds["u_24"] = ETLook.meteo.wind_speed(ds["u2m_24"], ds["v2m_24"])
    ds["ra_canopy_init"] = ETLook.neutral.initial_canopy_aerodynamic_resistance(ds["u_24"], ds["z0m"], z_obs = ds["z_obs"])

    # **windspeed blending height daily***********************************************************
    ds["u_b_24"] = ETLook.meteo.wind_speed_blending_height_daily(ds["u_24"], z_obs = ds["z_obs"], z_b = ds["z_b"])

    # **ETLook.neutral.initial_daily_transpiration***********************************************************
    ds["ad_dry_24"] = ETLook.meteo.dry_air_density_daily(ds["p_air_24"], ds["vp_24"], ds["t_air_k_24"])
    ds["ad_moist_24"] = ETLook.meteo.moist_air_density_daily(ds["vp_24"], ds["t_air_k_24"])
    ds["ad_24"] = ETLook.meteo.air_density_daily(ds["ad_dry_24"], ds["ad_moist_24"])
    ds["psy_24"] = ETLook.meteo.psychrometric_constant_daily(ds["p_air_24"], ds["lh_24"])
    ds["ssvp_24"] = ETLook.meteo.slope_saturated_vapour_pressure_daily(ds["t_air_24"])
    ds["t_24_init"] = ETLook.neutral.initial_daily_transpiration(ds["rn_24_canopy"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_canopy"], ds["ra_canopy_init"])

    # **ETLook.unstable.initial_sensible_heat_flux_canopy_daily***********************************************************
    ds["h_canopy_24_init"] = ETLook.unstable.initial_sensible_heat_flux_canopy_daily(ds["rn_24_canopy"], ds["t_24_init"])

    # **ETLook.unstable.initial_friction_velocity_daily***********************************************************
    #ds["disp"] = ETLook.roughness.displacement_height(ds["lai"], ds["z_obst"], land_mask = ds["land_mask"], c1 = ds["c1"])
    ds["disp"] = ETLook.roughness.displacement_height(ds["lai"], ds["z_obst"], land_mask = ds["land_mask"])
    ds["u_star_24_init"] = ETLook.unstable.initial_friction_velocity_daily(ds["u_b_24"], ds["z0m"], ds["disp"], z_b = ds["z_b"])

    # **ETLook.unstable.transpiration***********************************************************
    #ds["t_24"] = ETLook.unstable.transpiration(ds["rn_24_canopy"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_canopy"], ds["h_canopy_24_init"], ds["t_air_k_24"], ds["u_star_24_init"], ds["z0m"], ds["disp"], ds["u_b_24"], z_obs = ds["z_obs"], z_b = ds["z_b"], iter_h = ds["iter_h"])
    ds["t_24"] = ETLook.unstable.transpiration(ds["rn_24_canopy"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_canopy"], ds["h_canopy_24_init"], ds["t_air_k_24"], ds["u_star_24_init"], ds["z0m"], ds["disp"], ds["u_b_24"], z_obs = ds["z_obs"], z_b = ds["z_b"])
    ds["t_24_mm"] = ETLook.unstable.transpiration_mm(ds["t_24"], ds["lh_24"])

    #*******EVAPORATION COMPONENT****************************************************************

    # **ETLook.radiation.net_radiation_soil***********************************************************
    ds["rn_24_soil"] = ETLook.radiation.net_radiation_soil(ds["rn_24"], ds["sf_soil"])

    # **ETLook.resistance.soil_resistance***********************************************************
    #ds["r_soil"] = ETLook.resistance.soil_resistance(ds["se_root"], land_mask = ds["land_mask"], r_soil_pow = ds["r_soil_pow"], r_soil_min = ds["r_soil_min"])
    ds["r_soil"] = ETLook.resistance.soil_resistance(ds["se_root"], land_mask = ds["land_mask"])

    # **ETLook.resistance.soil_resistance***********************************************************
    ds["ra_soil_init"] = ETLook.neutral.initial_soil_aerodynamic_resistance(ds["u_24"], z_obs = ds["z_obs"])

    # **ETLook.unstable.initial_friction_velocity_soil_daily***********************************************************
    ds["u_star_24_soil_init"] = ETLook.unstable.initial_friction_velocity_soil_daily(ds["u_b_24"], ds["disp"], z_b = ds["z_b"])

    # **ETLook.unstable.initial_sensible_heat_flux_soil_daily***********************************************************
    ds["stc"] = ETLook.radiation.soil_thermal_conductivity(ds["se_root"])
    #ds["vhc"] = ETLook.radiation.volumetric_heat_capacity(ds["se_root"], porosity = ds["porosity"])
    ds["vhc"] = ETLook.radiation.volumetric_heat_capacity(ds["se_root"])

    ds["dd"] = ETLook.radiation.damping_depth(ds["stc"], ds["vhc"])
    ds["g0_bs"] = ETLook.radiation.bare_soil_heat_flux(ds["doy"], ds["dd"], ds["stc"], ds["t_amp"], ds["lat_rad"])
    ds["g0_24"] = ETLook.radiation.soil_heat_flux(ds["g0_bs"], ds["sf_soil"], ds["land_mask"], ds["rn_24_soil"], ds["trans_24"], ds["ra_24"], ds["l_net"], ds["rn_slope"], ds["rn_offset"])
    ds["e_24_init"] = ETLook.neutral.initial_daily_evaporation(ds["rn_24_soil"], ds["g0_24"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_soil"], ds["ra_soil_init"])
    ds["h_soil_24_init"] = ETLook.unstable.initial_sensible_heat_flux_soil_daily(ds["rn_24_soil"], ds["e_24_init"], ds["g0_24"])

    # **ETLook.unstable.evaporation***********************************************************
    #ds["e_24"] = ETLook.unstable.evaporation(ds["rn_24_soil"], ds["g0_24"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_soil"], ds["h_soil_24_init"], ds["t_air_k_24"], ds["u_star_24_soil_init"], ds["disp"], ds["u_b_24"], z_b = ds["z_b"], z_obs = ds["z_obs"], iter_h = ds["iter_h"])
    ds["e_24"] = ETLook.unstable.evaporation(ds["rn_24_soil"], ds["g0_24"], ds["ssvp_24"], ds["ad_24"], ds["vpd_24"], ds["psy_24"], ds["r_soil"], ds["h_soil_24_init"], ds["t_air_k_24"], ds["u_star_24_soil_init"], ds["disp"], ds["u_b_24"], z_b = ds["z_b"], z_obs = ds["z_obs"])
    ds["e_24_mm"] = ETLook.unstable.evaporation_mm(ds["e_24"], ds["lh_24"])
    ds["aeti_24_mm"] = ETLook.evapotranspiration.eti_actual_mm(ds["e_24_mm"], ds["t_24_mm"], ds["int_mm"])

    # **ETLook.unstable.evaporation***********************************************************
    #ds["rn_24_grass"] = ETLook.radiation.net_radiation_grass(ds["ra_24"], ds["l_net"], r0_grass = ds["r0_grass"])
    ds["rn_24_grass"] = ETLook.radiation.net_radiation_grass(ds["ra_24"], ds["l_net"])
    ds["et_ref_24"] = ETLook.evapotranspiration.et_reference(ds["rn_24_grass"], ds["ad_24"], ds["psy_24"], ds["vpd_24"], ds["ssvp_24"], ds["u_24"])
    ds["et_ref_24_mm"] = ETLook.evapotranspiration.et_reference_mm(ds["et_ref_24"], ds["lh_24"])

    '''
    ds["t_air_k_min"] = ETLook.meteo.air_temperature_kelvin_daily(ds["t_air_min_24"])
    ds["t_air_k_max"] = ETLook.meteo.air_temperature_kelvin_daily(ds["t_air_max_24"])

    ds["t_air_k_12"] = ETLook.meteo.mean_temperature_kelvin_daytime(ds["t_air_k_min"], ds["t_air_k_max"])

    ds["t_dep"] = ETLook.biomass.temperature_dependency(ds["t_air_k_12"], dh_ap=ds["dh_ap"], d_s=ds["d_s"], dh_dp=ds["dh_dp"])
    ds["k_m"] = ETLook.biomass.affinity_constant_co2(ds["t_air_k_12"])
    ds["k_0"] = ETLook.biomass.inhibition_constant_o2(ds["t_air_k_12"])
    ds["tau_co2_o2"] = ETLook.biomass.co2_o2_specificity_ratio(ds["t_air_k_12"])

    ds["year"] = ds.time_bins.dt.year.chunk("auto")

    ds["co2_act"] = ETLook.biomass.co2_level_annual(ds["year"])
    ds["a_d"] = ETLook.biomass.autotrophic_respiration(ds["t_air_k_24"], ar_slo=ds["ar_slo"], ar_int=ds["ar_int"])

    ds["apar"] = ETLook.biomass.par(ds["ra_24"])
    ds["f_par"] = ETLook.biomass.fpar(ds["ndvi"], fpar_slope=ds["fpar_slope"], fpar_offset=ds["fpar_offset"])

    ds["co2_fert"] = ETLook.biomass.co2_fertilisation(ds["tau_co2_o2"], ds["k_m"], ds["k_0"], ds["co2_act"], o2=ds["o2"], co2_ref=ds["co2_ref"])
    ds["npp_max"] = ETLook.biomass.net_primary_production_max(ds["t_dep"], ds["co2_fert"], ds["a_d"], ds["apar"], gcgdm=ds["gcgdm"])
    ds["npp"] = ETLook.biomass.net_primary_production(ds["npp_max"], ds["f_par"], ds["stress_moist"], phot_eff=ds["phot_eff"])
    '''

    ds = ds.drop_vars([x for x in ds.variables if ds[x].dtype == object])

    fp, fn = os.path.split(input_data)

    ds = g.variables.fill_attrs(ds)

    if export_vars == "all":
        ...
    elif export_vars == "default":
        keep_vars = [
                    'int_mm',
                    't_24_mm',
                    'e_24_mm',
                    'aeti_24_mm',
                    'se_root',
                    # 'npp'
                    ]
        keep_vars = [x for x in keep_vars if x in ds.variables]
        ds = ds[keep_vars]
    elif isinstance(export_vars, list):
        keep_vars = copy.copy(export_vars)
        ds = ds[keep_vars]
    else:
        raise ValueError(f"Please provide a valid `export_vars` ('all', 'default' or a list).")

    if len(ds.data_vars) == 0:
        log.info("--> No data to export, try adjusting `export_vars` or make sure to provide required inputs.")
        ds = None
    else:
        #ds = ds.transpose("time_bins", "y", "x") # set dimension order the same for all vars.
        ds = ds.transpose("time", "y", "x") # set dimension order the same for all vars.
        fn = fn.replace("in", "out")
        fp_out = os.path.join(fp, fn)
        if os.path.isfile(fp_out):
            fp_out = fp_out.replace(".nc", "_.nc")

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="invalid value encountered in power")
            warnings.filterwarnings("ignore", message="invalid value encountered in true_divide")
            warnings.filterwarnings("ignore", message="invalid value encountered in divide")
            warnings.filterwarnings("ignore", message="divide by zero encountered in power")
            warnings.filterwarnings("ignore", message="divide by zero encountered in true_divide")
            warnings.filterwarnings("ignore", message="divide by zero encountered in log")
            warnings.filterwarnings("ignore", message="divide by zero encountered in divide")
            ds = save_ds(ds, fp_out, encoding = "initiate", chunks = chunks, label = f"Saving output to `{fn}`.")

    t2 = datetime.datetime.now()
    log.sub().info(f"< ET_LOOK ({str(t2 - t1)})")

    return ds

def check_for_non_chuncked_arrays(ds):
    for var in ds.data_vars:
        if len(ds[var].dims) > 0:
            if isinstance(ds[var].chunks, type(None)):
                print(var)

if __name__ == "__main__":
    ...
    chunks = {"time_bins": -1, "x": 1000, "y": 1000}
    et_look_version = "v3"
    export_vars = "default"

    # input_data = '/Users/hmcoerver/Local/pywapor_se/et_look_in.nc'

    # input_data = r'/Users/hmcoerver/Local/test8/et_look_in_.nc'
    # et_look_version = "v2"
    # export_vars = "default"

    # out = main(input_data, et_look_version = et_look_version, export_vars = export_vars)
