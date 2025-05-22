# GEE_FANTA
An implementation of the Fallow-land Algorithm based on Neighborhood and Temporal Anomalies (FANTA) on Google Earth Engine (Python API + Jupyter Notebooks)

After: Cynthia S.A. Wallace, Prasad Thenkabail, Jesus R. Rodriguez & Melinda K. Brown (2017) Fallow-land Algorithm based on Neighborhood and Temporal Anomalies (FANTA) to map planted versus fallowed croplands using MODIS data to assist in drought studies leading to water and food security assessments, GIScience & Remote Sensing, 54:2, 258-282, DOI: 10.1080/15481603.2017.1290913

The algorithm is implemented as Jupyter notebook (GEE_FANTA.ipynb)

The normal usage of this workbook (i.e. with auto calibration disabled) produces an annual timeseries raster of fallowed pixels in the Google Drive associated with the account you are using for GEE.
The timeseries is encoded as raster bands in a geotiff file, with each band name encoding the year. Each pixel has a value of either 1 = fallow, or 0 = cultivated (or -9999 = NoData)

Parameters for the model are set in the second cell of the notebook.
This implementation supports the following surface reflectance products:
- `modis` : MODIS Terra.
- `sentinel` : Sentinel-2 MSI L2A. 
- `landsat` : Landsat-8 OLI Collection 2 Tier 1.
To select which dataset to use, adjust the `dataset` variable in the input cell.

This workbook also allows for possibility of auto calibration of the parameters using differential evolution algorithm.

If you want to use this workbook for your own region of interest, you need to supply a polygon asset (hosted in a GEE asset store you can access, e.g. your own GEE project) and set it as `roi` variable (as an ee.FeatureCollection). Ideally, this asset would have multiple polygons, each polygon covering a region with homogeneous climatic (and other) conditions (See the reference paper for more details).
Example ROIs are already set in the first cell (should be publicly accessible, unless I updated them and forgot to change permissions >_>)

In theory, any dataset with sufficient monthly rasters and enough bands to generate NDVI rasters (assuming we're sticking to the original research. Don't see why you can't test it with any other metric). All you need to do is adjust the third cell to create an ee.ImageCollection the rest of the code can work with.
