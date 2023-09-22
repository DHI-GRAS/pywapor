from setuptools import setup, find_packages

setup(
    name = 'pywapor',
    version = '3.4.2',
    url = 'https://www.fao.org/aquastat/py-wapor/',
    author = "FAO",
    author_email = "bert.coerver@fao.org",
    license = "Apache",
    packages = find_packages(include = ['pywapor', 'pywapor.*']),
    include_package_data=True,
    python_requires='>=3.7',
    install_requires = [
# - NOTE set libnetcdf=4.8 in conda otherwise this happend:
# https://github.com/pydata/xarray/issues/7549 (also see https://github.com/SciTools/iris/issues/5187)
        'netcdf4',
        'gdal',
        'xarray',
        'numpy',
        'pandas',
        'requests',
        'matplotlib',
        'pyproj',
        'scipy',
        'pycurl',
        'joblib',
        'bs4',
        'rasterio',
        'bottleneck',
        'tqdm',
        'dask',
        'rioxarray',
        'cryptography',
        'cachetools',
        'cdsapi',
        'shapely',
        'lxml',
        'scikit-learn',
        'numba',
        'xmltodict',
    ],
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)