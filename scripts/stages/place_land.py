"""Turn land pixels into grass, and edge the surrounding ocean with shoreline tiles."""

import numpy as np
from numpy.typing import NDArray

from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap


def _shift(land: NDArray[np.bool_], d_row: int, d_col: int) -> NDArray[np.bool_]:
    """Whether the neighbour at (row + d_row, col + d_col) is land, for every cell.

    Cells past the edge of the map copy the nearest in-bounds cell, so the map
    border never draws a shoreline on its own.
    """
    padded = np.pad(land, 1, mode="edge")
    height, width = land.shape
    return padded[1 + d_row : 1 + d_row + height, 1 + d_col : 1 + d_col + width]


def place_land(raster: Raster, tiles: Tilemap) -> Tilemap:
    """Set each tile from whether it and its neighbours are land or ocean.

    Grass is plain except along its top edge. The shoreline is otherwise drawn
    on the ocean tiles below, left and right of the grass. Combinations no tile
    covers (e.g. grass on both sides) fall back to the first matching rule.
    """
    land = np.equal(raster, Terrain.LAND)
    ocean = ~land
    n, w, e = _shift(land, -1, 0), _shift(land, 0, -1), _shift(land, 0, 1)
    nw, ne = _shift(land, -1, -1), _shift(land, -1, 1)

    # Earlier rules take precedence over later ones.
    rules: list[tuple[NDArray[np.bool_], Tile]] = [
        (land & ~n, Tile.GRASS_BELOW_OCEAN),
        (land, Tile.GRASS_CENTER),
        (ocean & n & w, Tile.OCEAN_BELOW_RIGHT_OF_GRASS),
        (ocean & n & e, Tile.OCEAN_BELOW_LEFT_OF_GRASS),
        (ocean & n, Tile.OCEAN_BELOW_GRASS),
        # Grass beside us with ocean above it is the top of a cliff run.
        (ocean & w & nw, Tile.OCEAN_RIGHT_OF_GRASS),
        (ocean & w, Tile.OCEAN_RIGHT_OF_GRASS_CORNER),
        (ocean & e & ne, Tile.OCEAN_LEFT_OF_GRASS),
        (ocean & e, Tile.OCEAN_LEFT_OF_GRASS_CORNER),
        (ocean & nw, Tile.OCEAN_BELOW_RIGHT_OF_GRASS_CORNER),
        (ocean & ne, Tile.OCEAN_BELOW_LEFT_OF_GRASS_CORNER),
    ]
    grid = np.select(
        [mask for mask, _ in rules],
        [int(tile) for _, tile in rules],
        default=int(Tile.OCEAN_CENTER),
    )

    for row, col in np.ndindex(grid.shape):
        tiles[row][col] = Tile(grid[row, col])
    return tiles
