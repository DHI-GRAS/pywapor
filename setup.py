from setuptools import setup, find_packages

setup(
    name = 'pywapor_test',
    version = '2.3.0',
    url = 'https://bitbucket.org/cioapps/wapor-et-look/src/master/',
    author = "FAO",
    author_email = "bert.coerver@fao.org",
    license = "Apache",
    packages = find_packages(include = ['pywapor', 'pywapor.*']),
    include_package_data=True,
    install_requires = [
        'gdal<=3.1.4',
        'aiohttp==3.7.4.post0',
        'numpy',
        'pandas',
        'requests',
        'matplotlib',
        'netcdf4',
        'pyproj',
        'scipy',
        'fiona',
        'pycurl',
        'pyshp',
        'joblib',
        'bs4',
        'paramiko',
        'rasterio',
        'xarray',
        'geojson',
        'vito_download',
        'nest_asyncio',
        'tqdm',
        'dask',
        'rioxarray',
        'ipympl',
    ]
)