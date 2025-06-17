#This script was created to export Sentinel-2 RGB (plus NIR band) images for validation purposes. Export is meant to show only a small region around specific points.
#Goal was to generate raster for any date in a specific month, covering a large area in total extents, but only few points of interests within it.
#This insues that even if the points' bounding box covers multiple longitude/latitude degrees, the output size will be few megatbytes.

#You need to provide a point vector asset.

#Note: the output has RGB channels ordered the correct way for display in desktop GIS software (e.g. QGIS), it uses default sentinel-2 DN encoding (0 to 10,000). Adjust
#your GIS software accordingely (for QGIS users, set min to 0 and max to 10000 for each band. You probably would also benefit from adjusting the gamme, contrast and saturation)
#For false colour imagery, some channel rearranging will be required (Map B8, B4, B2 to RGB channels)

import ee
ee.Initialize()

# points = ee.FeatureCollection("projects/seamproj01/assets/test_samples") 
# points = ee.FeatureCollection("projects/seamproj01/assets/test_samples_v1_1") 
points = ee.FeatureCollection("projects/seamproj01/assets/test_samples2") 

#set target year, months, and distance around the points to clip (in meters), and whether you want the resulting image to be split into four
year : int= 2020
months : list[int] = [6, 7, 8, 9, 10, 11]
distToClip : int = 1000
splitOutput : bool = False

maxImagesPerMonth = 3 #Must be greater than 0. Will prioritize least cloudy images. Will be capped to available dates.
#i.e. if maxImagesPerMonth = 1, then only the least cloudy image will be exported. if 2: least and second least. And so on.

#================================================
#Processing start
#================================================
sentinel2SR = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")

#buffer the points to create rois to clip
roi = points.map(lambda point : point.buffer(distToClip)) #note: this will use meters, but on a spherical coordinate system. check the docs.
#buffer on a point returns a circle, let's convert it to a rectangle. Not necessary, but I like rects better for these kinda things :) Using the circles bounds simplifis this.
roi = roi.map(lambda circle : ee.Geometry.Rectangle(ee.Array.cat(circle.geometry().bounds().coordinates(),1).slice(0, 0, 3, 2).reshape([-1]).toList()))


for month in months:
        #pre filtering the images
        col : ee.ImageCollection = sentinel2SR.filterDate(f"{year}-{month}-01", f"{year}-{month + 1}-1" if month < 12 else  f"{year + 1}-1-1").filterBounds(roi.geometry())
        col = col.select(['B4', 'B3', 'B2', 'B8'])
        #add a formatted date property (makes our life easier)
        col = col.map(lambda img : img.set({"date" : ee.Date(img.get("system:time_start")).format("y-M-d")}))

        #mosaic the images in a single date into one image
        dates = col.aggregate_array("date").distinct().getInfo()
        monthImages = ee.List([])

        for date in dates:
                subCol = col.filter(ee.Filter.eq("date", date))
                meanCloudyPercentage = subCol.aggregate_array("CLOUDY_PIXEL_PERCENTAGE").reduce(ee.Reducer.mean())
                monthImages = monthImages.add(subCol.mosaic().set({"date" : date, "CLOUDY_PIXEL_PERCENTAGE" : meanCloudyPercentage}))
        
        #convert to an image collection, then sort based on cloud percentage.
        monthImages = ee.ImageCollection(monthImages).sort("CLOUDY_PIXEL_PERCENTAGE")
        #convert back to list because we need to iterate through them in order
        monthImages = monthImages.toList(monthImages.size())
        
        for i in range (0, min(maxImagesPerMonth, monthImages.size().getInfo())):
                targetImageLarge = ee.Image(monthImages.get(i)).clip(roi.geometry())

                if not splitOutput:
                        outputFileName = f"RGBNir_{targetImageLarge.get("date").getInfo()}"

                        print ("exporting: ", outputFileName)

                        task = ee.batch.Export.image.toDrive(
                                                                image = targetImageLarge,
                                                                description = outputFileName,
                                                                #folder='ee_export',
                                                                #region = quadrants[i],
                                                                scale = 10,
                                                                crs = 'EPSG:4326',
                                                                maxPixels = 3e10,
                                                                fileFormat = 'GeoTIFF',
                                                                formatOptions = {
                                                                        'noData': 0
                                                                })      
                        task.start()

                else:
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
                                outputFileName = f"RGBNir_{targetImageLarge.get("date").getInfo()}_part_{i}"

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