#This script was created to export Sentinel-2 RGB (plus NIR band) images for validation purposes. Export is meant to show only a small region around specific points.
#Goal was to generate raster for any date in a specific month, covering a large area in total extents, but only few points of interests within it.
#This insues that even if the points' bounding box covers multiple longitude/latitude degrees, the output size will be few megatbytes.

#For optimal performance, the roi should be rectangular polygons around your validation points. Large enough that to show enough features to make a conclusion.
#atm, this roi should be prepared in any GIS software that can produce shp files for earth engine to ingest
#TODO consider doing the sampling itself in GEE, and export both the generated points and the imagery.

#Note: the output has RGB channels ordered the correct way for display in desktop GIS software (e.g. QGIS), it uses default sentinel-2 DN encoding (0 to 10,000). Adjust
#your GIS software accordingely (for QGIS users, set min to 0 and max to 10000 for each band. You probably would also benefit from adjusting the gamme, contrast and saturation)
#For false colour imagery, some channel rearranging will be required (Map B8, B4, B2 to RGB channels)

import ee
ee.Initialize()

sentinel2SR = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
points = ee.FeatureCollection("projects/seamproj01/assets/test_samples") 

#set target year and month, and distance around the points to clip (in meters)
year = 2019
month = 6
distToClip = 1000

#buffer the points to create rois to clip
roi = points.map(lambda point : point.buffer(distToClip)) #note: this will use meters, but on a spherical coordinate system. check the docs.
#buffer on a point returns a circle, let's convert it to a rectangle. Not necessary, but I like rects better for these kinda things :) Using the circles bounds simplifis this.
roi = roi.map(lambda circle : ee.Geometry.Rectangle(ee.Array.cat(circle.geometry().bounds().coordinates(),1).slice(0, 0, 3, 2).reshape([-1]).toList()))

#pre filtering the images
col = sentinel2SR.filterDate(f"{year}-{month}-01", f"{year}-{month + 1}-1" if month < 12 else  f"{year + 1}-1-1").filterBounds(roi.geometry())
col = col.select(['B4', 'B3', 'B2', 'B8'])

#generate a single composite/mosaic of the entire roi, using the least cloudy images for the month
#First, get a list of MRGS tiles covering the points.
tileList = col.distinct("MGRS_TILE").aggregate_array("MGRS_TILE").getInfo()

#Note: Sentinel-2 Data aren't always produced as perfect rectangles fitting an MGRS tiles. Some tiles are covered by the triangular/trapizoilda remainder of a sentine scene
#after clipping neighbouring tiles. So, we do an internal mosaic for this tile first (inside the loop bellow), before doing the mosaicing over all tiles
bestScences = ee.List([])
for tileID in tileList:
    #mosaic puts last image on top, so you want your least cloudy image as the last one.
    tileCol = col.filter(ee.Filter.eq("MGRS_TILE", tileID)).sort("CLOUDY_PIXEL_PERCENTAGE", False)
    tileImg = tileCol.mosaic()
    bestScences = bestScences.add(tileImg)

bestScences = ee.ImageCollection(bestScences)
targetImageLarge = bestScences.mosaic().clip(roi.geometry()).toInt16()

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
        outputFileName = f"RGB_{year}_{month}_part_{i}"

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