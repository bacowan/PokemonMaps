"""Turn land pixels into grass, and edge the surrounding ocean with shoreline tiles."""

import numpy as np

from stages.neighbours import Neighbours
from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap


def place_land(raster: Raster, tiles: Tilemap) -> Tilemap:
    """Set every tile to grass or ocean, with a shoreline where they meet."""
    for row, col in np.ndindex(raster.shape):
        tiles[row][col] = _land_tile(Neighbours.around(raster, row, col))
    return tiles


def _land_tile(cell: Neighbours) -> Tile:
    """Pick a tile from whether the cell and its neighbours are land.

    Anything that isn't land counts as ocean here. Grass is plain except along
    its top edge; the rest of the shoreline is drawn on the ocean tiles below,
    left and right of the grass. Combinations no tile covers (e.g. grass on
    both sides) use whichever branch comes first.
    """
    here = cell.here == Terrain.LAND
    above = cell.above == Terrain.LAND
    left = cell.left == Terrain.LAND
    right = cell.right == Terrain.LAND
    above_left = cell.above_left == Terrain.LAND
    above_right = cell.above_right == Terrain.LAND

    if here:
        return Tile.GRASS if above else Tile.GRASS_OCEAN_N

    if above and left:
        return Tile.OCEAN_GRASS_NW_INNER
    if above and right:
        return Tile.OCEAN_GRASS_NE_INNER
    if above:
        return Tile.OCEAN_GRASS_N
    # Grass beside us with grass above it continues a cliff; without, it's the top corner.
    if left:
        return Tile.OCEAN_GRASS_W if above_left else Tile.OCEAN_GRASS_W_OUTER
    if right:
        return Tile.OCEAN_GRASS_E if above_right else Tile.OCEAN_GRASS_E_OUTER
    if above_left:
        return Tile.OCEAN_GRASS_NW_OUTER
    if above_right:
        return Tile.OCEAN_GRASS_NE_OUTER
    return Tile.OCEAN
