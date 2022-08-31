## pyWaPOR

![downloads](https://img.shields.io/pypi/dw/pywapor) [![version](https://img.shields.io/pypi/v/pywapor)](https://pypi.org/project/pywapor/) [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/1_introduction.ipynb)  

This repository contains a Python implementation of the algorithm used to generate the [WaPOR](http://www.fao.org/in-action/remote-sensing-for-water-productivity/en/) [datasets](https://wapor.apps.fao.org/home/WAPOR_2/1). It can be used to calculate evaporation, transpiration and biomass production maps.

### Installation

Its recommended to install in a clean [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) and use [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) to install all the important packages from the `conda-forge` channel.

```bash
conda create -n my_pywapor_env --yes -c conda-forge python pip gdal pydap numpy pandas requests matplotlib pyproj scipy pycurl pyshp joblib bs4 rasterio xarray bottleneck geojson tqdm dask rioxarray pyvis shapely lxml cachetools cdsapi sentinelsat geopy 

conda activate my_pywapor_env
```

Then use the package manager [pip](https://pip.pypa.io/en/stable/) to install pywapor.

```bash
pip install pywapor
```

### Usage

To run the model for one dekad (from 2021-07-01 to 2021-07-11 in this case) for the Fayoum irrigation scheme in Egypt (but feel free to change the [boundingbox](http://bboxfinder.com) defined by `latlim` and `lonlim`) using mainly MODIS data, run the following code. 

```python
import pywapor

# User inputs.
timelim = ["2021-07-01", "2021-07-11"]
latlim = [28.9, 29.7]
lonlim = [30.2, 31.2]
project_folder = r"/my_first_ETLook_run/"

# Download and prepare input data.
ds_in  = pywapor.pre_et_look.main(project_folder, latlim, lonlim, timelim)

# Run the model.
ds_out = pywapor.et_look.main(ds_in)
```

Check out the documentation and the notebooks below to learn more!

### Documentation
Go [here](https://www.fao.org/aquastat/py-wapor/) for the full pyWaPOR documentation.

#### Notebooks

<table class = "docutils align-default">
   <thead>
      <tr class="row-odd" style="text-align:center">
         <th class="head"></th>
         <th class="head">Name</th>
         <th class="head" width = "150">Colab</th>
      </tr>
   </thead>
   <tbody>
      <tr class="row-odd">
         <td>1.</td>
         <td>Introduction</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/1_introduction.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
      <tr class="row-even">
         <td>2.</td>
         <td>Levels</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/2_levels.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
      <tr class="row-odd">
         <td>3.</td>
         <td>Composites</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/3_composites.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
      <tr class="row-even">
         <td>4.</td>
         <td>Sideloading</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/4_sideloading.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
      <tr class="row-odd">
         <td>5.</td>
         <td>Enhancers</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/5_enhancers.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
      <tr class="row-even">
         <td>6.</td>
         <td>pyWaPOR vs. WaPOR</td>
         <td style="text-align:center"><a href="https://colab.research.google.com/github/bertcoerver/pywapor_notebooks/blob/main/6_wapor_vs_pywapor.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="colab"/></a></td>
      </tr>
   </tbody>
</table>

#### WaPOR v2

<ul>
<li><a href="https://bitbucket.org/cioapps/wapor-et-look/downloads/FRAME_ET_v2_data_manual_finaldraft_v2.2.pdf">WaPOR-ETLook Data Manual (v2)</a></li>

<li><a href="https://bitbucket.org/cioapps/wapor-et-look/downloads/FRAME_NPP_v2_data_manual_finaldraft_v2.2.pdf">WaPOR-Biomass Data Manual (v2)</a></li>
</ul>

#### WaPOR v1

<ul>
<li><a href="https://bitbucket.org/cioapps/wapor-et-look/raw/9ec88e56769f49722c2d1165bb34547f5842b811/Docs/WaPOR_ET_data_manual_finaldraft-v1.2-for-distribution.pdf">WaPOR-ETLook Data Manual (v1)</a></li>
</ul>

### Acknowledgments
The methodology for WaPOR was developed by the FRAME1 consortium, consisting of eLEAF (lead), VITO, ITC, University of Twente and Waterwatch foundation, commissioned by and in partnership with the Land and Water Division of FAO. The method for calculating evapotranspiration is based on the ETLook model developed by eLEAF in 2010. The method for calculating total biomass production is based on the C-Fix model. 

The code in the pywapor.et_look_v2 module of this repository, containing all core physical functions used by ETLook, was written by Henk Pelgrum (eLEAF) and Rutger Kassies (eLEAF). The remaining modules have been developed by Bert Coerver (FAO), Tim Hessels (WaterSat), and, in the framework of the ESA-funded ET4FAO project, Radoslaw Guzinski (DHI-GRAS), Hector Nieto (Complutig) and Laust Faerch (DHI-GRAS).

### Contact
For questions, requests or issues with this repository, please contact Bert Coerver at [bert.coerver@fao.org](mailto:bert.coerver@fao.org) or the WaPOR team at [wapor@fao.org](mailto:wapor@fao.org).

### Release Notes

#### 3.0.0 (2022-08-31)
<br>
<ul>
    <li> Bugfixes. Most noteably, server side errors when downloading data are now handeled better, i.e. collect tools will retry several times when a download fails, but many other smaller issues have been fixed too.</li>
    <li> Performance improvements, mostly due to fewer reprojections. </li>
    <li> Better logging. The logs from SENTINEL and ERA5 are now directed to seperate channels and logs now show peak-memory-usage for critical calculation steps.
    <li> `et_look` and `se_root` now accept a `chunks` keyword to adjust the chunksizes at which the calculations are done. Increase them if you have a lot of RAM available, decrease them for slower calculations but with less memory usage.</li>
    <li> Support for WaPOR v3 methodology. Choose `et_look_version = "v3"` and `se_root_version = "v3"` when running the respective models (`et_look` and `se_root`).</li>
    <li> Default configurations for WaPOR v3 input datasets, i.e. choose `sources = "level_2_v3"` when running `pre_et_look` or `pre_se_root`.
    <li> New collect functions for COPERNICUS DEM. </li>
    <li> The data structure for STATICS is now consistent with the other products. </li>
</ul>

#### 2.6.0 (2022-08-04)
<br>
<ul>
    <li> New collect functions for VIIRS (Level-1), SENTINEL-2, SENTINEL-3 and (ag)ERA5.</li>
    <li> pyWaPOR now works with Python versions greater than 3.8.
</ul>

#### 2.5.0 (2022-06-23)
<br>
<ul>
    <li> Rewritten collect tools.</li>
    <li> The entire workflow now works with netCDF.</li>
    <li> All the netCDF files are formatted to support the <a href = "https://corteva.github.io/rioxarray/stable/getting_started/getting_started.html">rio-acccessor</a>.</li>
</ul>

#### 2.4.2 (2022-04-26)
<br>
<ul>
    <li> New biomass module and NPP calculation.</li>
</ul>

#### 2.4.1 (2022-03-11)
<br>
<ul>
    <li> NetCDF files are now compressed when saved to disk.</li>
    <li> Calculation of Total Biomass Production is now turned on by default.</li>
    <li> It is no longer required to provide <b>all</b> input variables to et_look,
    the model will calculate as many variables as possible with the given data. For example,
    if you are only interested in acquiring interception rates, it would now suffice to only prepare ndvi and p (precipitation) data with pre_et_look.</li>
    <li> et_look now automatically generates an interactive network graph visualising the executed computation steps.</li>
</ul>

#### 2.4.0 (2022-02-03)
<br>
<ul>
    <li> Easily apply your own functions to data, i.e. use your own custom filters, gap-fillers etc.</li>
    <li> Side-load your own data, i.e. easily incorporate you own datasets.</li>
    <li> Added functions to process Landsat Level-2 to “ndvi”, “lst” and “r0”.</li>
    <li> Data is now stored and processed as netCDF (using xarray and dask).</li>
    <li> Calculations in et_look() and se_root() are now done in chunks, instead of using a for-loop.</li>
    <li> Some previously constant parameters now have spatial variability.</li>
    <li> Improved logging.</li>
    <li> Download functions now show progress and download-speed.</li>
    <li> MODIS datasets switched from v6.0 (decommissioned soon) to v6.1.</li>
    <li> The lapse-rate correction to temperature data is now more accurate and faster.</li>
    <li> VITO and WAPOR passwords are now checked when entered.</li>
    <li> Other bug-fixes and performance improvements.</li>
</ul>

#### 2.3.0 (2021-11-19)
<br>
<ul> 
    <li>Automatically create input composites before running ETLook.</li>
    <li>Choose composite lengths in number of days or dekads.</li>
    <li>Option to choose which products to use per variable.</li>
    <li>Calculate soil saturation separate from ETLook.</li>
    <li>PROBA-V support for NDVI and Albedo inputs.</li>
    <li>Define diagnostics pixels, for which extra outputs are created (e.g. charts, maps etc.).</li>
    <li>Bug-fixes and performance improvements.</li>
</ul>

### License
[APACHE](https://bitbucket.org/cioapps/wapor-et-look/src/dev/LICENSE)