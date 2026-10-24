"""Picking each tile by matching its cell's 3x3 neighbourhood against masks.

The config (masks.json by default) maps each Terrain to the masks for cells of
that terrain. A mask is a 3x3 grid laid out as on the map (first row above the
cell); a cell's masks are tried in order and the first match wins. The centre
of each grid names the Tile to use; every other entry is the Terrain that
neighbour must be, or "*" for anything:
  {
    "SAND": [
      [["*", "OCEAN",        "*"],
       ["*", "SAND_OCEAN_N", "*"],
       ["*", "*",            "*"]],
      ...
    ],
    ...
  }

Cells past the edge of the map copy the nearest in-bounds cell, so the map
border never draws an edge on its own.
"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap

MASKS_JSON = Path(__file__).with_name("masks.json")
ANY = "*"
CENTRE = (1, 1)


@dataclass(frozen=True)
class Mask:
    tile: Tile
    neighbours: dict[tuple[int, int], Terrain]
    """The terrain required at each (row, col) of the 3x3 window; "*" entries are left out."""

    def matches(self, window: Raster) -> bool:
        return all(window[pos] == terrain for pos, terrain in self.neighbours.items())


type Masks = dict[Terrain, list[Mask]]
"""The masks to try, in order, for cells of each terrain."""


def load_masks(path: Path = MASKS_JSON) -> Masks:
    """Read the mask config, failing on missing terrain, bad shapes or unknown names."""
    data: dict[str, list[list[list[str]]]] = json.loads(path.read_text())
    problems: list[str] = []
    missing = [terrain.name for terrain in Terrain if terrain.name not in data]
    extra = [name for name in data if name not in Terrain.__members__]
    if missing:
        problems.append(f"missing terrain: {', '.join(missing)}")
    if extra:
        problems.append(f"unknown terrain: {', '.join(extra)}")
    masks: Masks = {}
    for name, grids in data.items():
        if name in Terrain.__members__:
            masks[Terrain[name]] = _parse_masks(f"{name} mask", grids, problems)
    if problems:
        raise ValueError(f"{path}:\n  " + "\n  ".join(problems))
    return masks


def _parse_masks(label: str, grids: list[list[list[str]]], problems: list[str]) -> list[Mask]:
    """Parse one terrain's grids, appending anything wrong with them to problems."""
    masks: list[Mask] = []
    for index, grid in enumerate(grids):
        where = f"{label} {index}"
        if len(grid) != 3 or any(len(row) != 3 for row in grid):
            problems.append(f"{where}: must be 3x3")
            continue
        centre = grid[1][1]
        if centre not in Tile.__members__:
            problems.append(f"{where}: unknown tile {centre}")
            continue
        neighbours: dict[tuple[int, int], Terrain] = {}
        for pos in np.ndindex(3, 3):
            entry = grid[pos[0]][pos[1]]
            if pos == CENTRE or entry == ANY:
                continue
            if entry not in Terrain.__members__:
                problems.append(f"{where} ({centre}): unknown terrain {entry}")
                continue
            neighbours[pos] = Terrain[entry]
        masks.append(Mask(Tile[centre], neighbours))
    return masks


def windows(raster: Raster) -> Iterator[tuple[int, int, Raster]]:
    """Yield (row, col, 3x3 window centred on that cell) for every cell."""
    padded = np.pad(raster, 1, mode="edge")
    for row, col in np.ndindex(raster.shape):
        yield row, col, padded[row : row + 3, col : col + 3]


def pick_tile(masks: Sequence[Mask], window: Raster) -> Tile:
    """The tile of the first mask matching the window."""
    for mask in masks:
        if mask.matches(window):
            return mask.tile
    raise ValueError(f"no mask matches window:\n{window}")


def place_tiles(raster: Raster, masks: Masks) -> Tilemap:
    """Pick every cell's tile from the masks for its terrain."""
    height, width = raster.shape
    tiles: Tilemap = [[Tile.OCEAN] * width for _ in range(height)]
    for row, col, window in windows(raster):
        tiles[row][col] = pick_tile(masks[Terrain(raster[row, col])], window)
    return tiles
