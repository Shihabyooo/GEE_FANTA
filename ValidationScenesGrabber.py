#This script was created to export Sentinel-2 RGB (plus NIR band``) images for validation purposes. Export is meant to show only a small region around specific points.
#Goal was to generate raster for any date in a specific month, covering a large area in total extents, but only few points of interests within it.
#This insues that even if the points' bounding box covers multiple longitude/latitude degrees, the output size will be in few megatbytes.

#For optimal performance, the roi should be rectangular polygons around your validation points. Large enough that to show enough features to make a conclusion.
#atm, this roi should be prepared in any GIS software that can produce shp files for earth engine to ingest.
#TODO modify code to ingest points, and do the buffering in GEE.
#TODO consider doing the sampling itself in GEE, and export both the generated points and the imagery.

#Note: the output has RGB channels ordered the correct way for display in desktop GIS software (e.g. QGIS), it uses default sentinel-2 DN encoding (0 to 10,000). Adjust
#your GIS software accordingely (for QGIS users, set min to 0 and max to 10000 for each band. You probably would also benefit from adjusting the gamme, contrast and saturation)
#For false colour imagery, some channel rearranging will be required.

import ee
ee.Initialize(project='seamproj01')

sentinel2SR = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
roi = ee.FeatureCollection("projects/seamproj01/assets/sampling_points_buffer_1km_v2") 

#set target year and month
year = 2019
month = 7

#set maximum cloud percentage of a scene to be allowed in a mosaic (note: even if a scene passed this check, this doesn't guarantee its mosaic will be used)
cloudThreshold = 25

#pre-filter the sentinel collection and add doy identifier, which will be used to mosaic scenes.
col = sentinel2SR.filterDate(f"{year}-{month}-01", f"{year}-{month + 1}-1" if month < 12 else  f"{year + 1}-1-1").filterBounds(roi.geometry())
col = col.filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloudThreshold))
col = col.map(lambda img : img.set({"doy" : ee.Date(img.get("system:time_start")).format("DD")}))

doyList = col.distinct("doy").aggregate_array("doy").getInfo()

mosaicList = ee.List([])
for doy in doyList:
    scenesInDoY = col.filter(ee.Filter.eq("doy", doy))
    mosaic = scenesInDoY.select(['B4', 'B3', 'B2', 'B8']).mosaic().clip(roi.geometry()).toInt16().set({"doy" : doy, "count" : scenesInDoY.size()})
    mosaicList =  mosaicList.add(mosaic)

mosaicList = ee.ImageCollection(mosaicList)

#sort and pick image with most scenes (ideally, covering our entire roi)
mosaicList = mosaicList.sort("count", False)
targetImageLarge = mosaicList.first()

#To split the image into four, first, compute the bounds for splitting (quardants)
boundingBox = ee.Array.cat(roi.geometry().bounds().coordinates(), 1)

xCoords = boundingBox.slice(1, 0, 1)
yCoords = boundingBox.slice(1, 1, 2)
xMin = xCoords.reduce('min', [0]).get([0,0])
xMax = xCoords.reduce('max', [0]).get([0,0])
yMin = yCoords.reduce('min', [0]).get([0,0])
yMax = yCoords.reduce('max', [0]).get([0,0])

xHalf = xMin.add(xMax).divide(2.0)
yHalf = yMin.add(yMax).divide(2.0)

#ee.Geometry.BBox(west, south, east, north)
quadrants = []
quadrants.append(ee.Geometry.BBox(xMin, yMin, xHalf, yHalf))
quadrants.append(ee.Geometry.BBox(xHalf, yMin, xMax, yHalf))
quadrants.append(ee.Geometry.BBox(xHalf, yHalf, xMax, yMax))
quadrants.append(ee.Geometry.BBox(xMin, yHalf, xHalf, yMax))

#export
for i in range (0, 4):
        outputFileName = f"RGB_{year}_{month}_{targetImageLarge.get("doy").getInfo()}_part_{i}"

        print ("exporting: ", outputFileName)
        targetImage = targetImageLarge.clip(quadrants[i])

        task = ee.batch.Export.image.toDrive(
        image = targetImage,
        description = outputFileName,
        #folder='ee_export',
        region = quadrants[i],
        scale = 10,
        crs = 'EPSG:4326',
        maxPixels = 200000000,
        fileFormat = 'GeoTIFF',
        formatOptions = {
                'noData': 0
        })
        task.start()