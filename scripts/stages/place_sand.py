"""Turn sand pixels into sand, edged with grass or ocean where it meets them."""

import numpy as np
from numpy.typing import NDArray

from stages.place_land import _shift as shift
from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap

# Edge tiles by which sides face away from the sand, for sand bordered by
# grass and by ocean. Keys are (top, bottom, left, right) edges.
_EDGES: dict[tuple[bool, bool, bool, bool], tuple[Tile, Tile]] = {
    (True, False, True, False): (Tile.SAND_BELOW_RIGHT_OF_GRASS, Tile.SAND_BELOW_RIGHT_OF_OCEAN),
    (True, False, False, True): (Tile.SAND_BELOW_LEFT_OF_GRASS, Tile.SAND_BELOW_LEFT_OF_OCEAN),
    (False, True, True, False): (Tile.SAND_ABOVE_RIGHT_OF_GRASS, Tile.SAND_ABOVE_RIGHT_OF_OCEAN),
    (False, True, False, True): (Tile.SAND_ABOVE_LEFT_OF_GRASS, Tile.SAND_ABOVE_LEFT_OF_OCEAN),
    (True, False, False, False): (Tile.SAND_BELOW_GRASS, Tile.SAND_BELOW_OCEAN),
    (False, True, False, False): (Tile.SAND_ABOVE_GRASS, Tile.SAND_ABOVE_OCEAN),
    (False, False, True, False): (Tile.SAND_RIGHT_OF_GRASS, Tile.SAND_RIGHT_OF_OCEAN),
    (False, False, False, True): (Tile.SAND_LEFT_OF_GRASS, Tile.SAND_LEFT_OF_OCEAN),
}


def place_sand(raster: Raster, tiles: Tilemap) -> Tilemap:
    """Set each sand tile from which of its sides border something else.

    Sand draws its own edge, against ocean if any bordering side is ocean and
    against grass otherwise. Combinations no tile covers (e.g. edges on
    opposite sides) fall back to the first matching rule, as in place_land.
    """
    sand = np.equal(raster, Terrain.SAND)
    ocean = np.equal(raster, Terrain.OCEAN)
    top, bottom = ~shift(sand, -1, 0), ~shift(sand, 1, 0)
    left, right = ~shift(sand, 0, -1), ~shift(sand, 0, 1)
    faces_ocean = (
        (top & shift(ocean, -1, 0))
        | (bottom & shift(ocean, 1, 0))
        | (left & shift(ocean, 0, -1))
        | (right & shift(ocean, 0, 1))
    )

    # Earlier rules take precedence over later ones.
    rules: list[tuple[NDArray[np.bool_], Tile]] = []
    for (t, b, l, r), (grass_tile, ocean_tile) in _EDGES.items():
        edge = sand & (top if t else True) & (bottom if b else True) & (left if l else True) & (right if r else True)
        rules.append((edge & faces_ocean, ocean_tile))
        rules.append((edge & ~faces_ocean, grass_tile))
    grid = np.select(
        [mask for mask, _ in rules] + [sand],
        [int(tile) for _, tile in rules] + [int(Tile.SAND_CENTER)],
        default=-1,
    )

    for row, col in zip(*np.nonzero(grid >= 0)):
        tiles[row][col] = Tile(grid[row, col])
    return tiles
