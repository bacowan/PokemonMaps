"""Turn every land pixel in the raster into grass."""

import numpy as np

from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap


def place_land(raster: Raster, tiles: Tilemap) -> Tilemap:
    """Set the tile to grass wherever the raster is land."""
    for row, col in zip(*np.nonzero(np.equal(raster, Terrain.LAND))):
        tiles[row][col] = Tile.GRASS_CENTER
    return tiles
