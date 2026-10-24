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
    against grass otherwise. When ocean borders the cell only the ocean sides
    count as edges, so the coast faces the water even with grass on another
    side. Combinations no tile covers (e.g. edges on opposite sides) use
    whichever branch comes first.
    """
    sides = [cell.above, cell.below, cell.left, cell.right]
    of_ocean = Terrain.OCEAN in sides
    if of_ocean:
        above, below, left, right = (side == Terrain.OCEAN for side in sides)
    else:
        above, below, left, right = (side != Terrain.SAND for side in sides)

    if above and left:
        return Tile.SAND_OCEAN_NW if of_ocean else Tile.SAND_GRASS_NW
    if above and right:
        return Tile.SAND_OCEAN_NE if of_ocean else Tile.SAND_GRASS_NE
    if below and left:
        return Tile.SAND_OCEAN_SW if of_ocean else Tile.SAND_GRASS_SW
    if below and right:
        return Tile.SAND_OCEAN_SE if of_ocean else Tile.SAND_GRASS_SE
    if above:
        return Tile.SAND_OCEAN_N if of_ocean else Tile.SAND_GRASS_N
    if below:
        return Tile.SAND_OCEAN_S if of_ocean else Tile.SAND_GRASS_S
    if left:
        return Tile.SAND_OCEAN_W if of_ocean else Tile.SAND_GRASS_W
    if right:
        return Tile.SAND_OCEAN_E if of_ocean else Tile.SAND_GRASS_E
    return Tile.SAND
