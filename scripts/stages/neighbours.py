"""Looking up the terrain around a single raster cell."""

from dataclasses import dataclass

from terrain import Terrain
from tilemap import Raster


@dataclass(frozen=True)
class Neighbours:
    """The terrain of a cell and the cells around it.

    Cells past the edge of the map copy the nearest in-bounds cell, so the map
    border never draws an edge on its own.
    """

    here: Terrain
    above: Terrain
    below: Terrain
    left: Terrain
    right: Terrain
    above_left: Terrain
    above_right: Terrain

    @staticmethod
    def around(raster: Raster, row: int, col: int) -> "Neighbours":
        height, width = raster.shape

        def at(d_row: int, d_col: int) -> Terrain:
            r = min(max(row + d_row, 0), height - 1)
            c = min(max(col + d_col, 0), width - 1)
            return Terrain(raster[r, c])

        return Neighbours(
            here=at(0, 0),
            above=at(-1, 0),
            below=at(1, 0),
            left=at(0, -1),
            right=at(0, 1),
            above_left=at(-1, -1),
            above_right=at(-1, 1),
        )
