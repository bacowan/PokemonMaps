"""Turn sand pixels into sand, edged with grass or ocean where it meets them."""

import numpy as np

from stages.neighbours import Neighbours
from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap


def place_sand(raster: Raster, tiles: Tilemap) -> Tilemap:
    """Set every sand tile, leaving the rest of the tilemap as it is."""
    for row, col in np.ndindex(raster.shape):
        if raster[row, col] == Terrain.SAND:
            tiles[row][col] = _sand_tile(Neighbours.around(raster, row, col))
    return tiles


def _sand_tile(cell: Neighbours) -> Tile:
    """Pick a tile from which sides of the cell border something other than sand.

    Sand draws its own edge, against ocean if any bordering side is ocean and
    against grass otherwise. Combinations no tile covers (e.g. edges on
    opposite sides) use whichever branch comes first.
    """
    sides = [cell.above, cell.below, cell.left, cell.right]
    above, below, left, right = (side != Terrain.SAND for side in sides)
    of_ocean = Terrain.OCEAN in sides

    if above and left:
        return Tile.SAND_BELOW_RIGHT_OF_OCEAN if of_ocean else Tile.SAND_BELOW_RIGHT_OF_GRASS
    if above and right:
        return Tile.SAND_BELOW_LEFT_OF_OCEAN if of_ocean else Tile.SAND_BELOW_LEFT_OF_GRASS
    if below and left:
        return Tile.SAND_ABOVE_RIGHT_OF_OCEAN if of_ocean else Tile.SAND_ABOVE_RIGHT_OF_GRASS
    if below and right:
        return Tile.SAND_ABOVE_LEFT_OF_OCEAN if of_ocean else Tile.SAND_ABOVE_LEFT_OF_GRASS
    if above:
        return Tile.SAND_BELOW_OCEAN if of_ocean else Tile.SAND_BELOW_GRASS
    if below:
        return Tile.SAND_ABOVE_OCEAN if of_ocean else Tile.SAND_ABOVE_GRASS
    if left:
        return Tile.SAND_RIGHT_OF_OCEAN if of_ocean else Tile.SAND_RIGHT_OF_GRASS
    if right:
        return Tile.SAND_LEFT_OF_OCEAN if of_ocean else Tile.SAND_LEFT_OF_GRASS
    return Tile.SAND_CENTER
