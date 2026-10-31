# Order of operations
## Manual through QGIS
1. Download layers through QuickOSM Plugin
2. Make sure that layers are projected with EPSG:6677
3. Create a raster layer. Set its data type to byte
4. For each layer, project it to the raster layer (Processing toolbox -> Rasterize (Overwrite with Fixed Value)) and use a new value for each
5. Map flags to values (right click on raster layer -> properties -> symbology -> classify)

# How to
## Finding features to download
- go to openstreetmap.org, right click on the map somewhere, and select query features. This will tell you what features the point has and that you can use to query the point
- https://overpass-turbo.eu/ to test queries
- https://wiki.openstreetmap.org/wiki/Map_features for docs on features

# Useful Features
- "natural"="water" for water
- "natural"="beach" for beaches
- "highway"="primary" for inner city roads
- "highway"="motorway" or "highway"="trunk" for highways
