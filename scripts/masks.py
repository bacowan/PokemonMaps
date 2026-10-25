"""Picking each tile by matching its cell's 3x3 neighbourhood against masks.

The config (masks.json by default) is a list of masks, tried in order for every
cell; the first match wins. Each mask has a unique name (shown as "rule" in the
frontend's debug tooltip), the Tile to use and a 3x3 grid laid out as on the map
(first row above the cell, centre the cell itself), one space-separated string
per row. Every entry, centre included, is the Terrain that cell must be, "!" and
a Terrain for anything but that one, or "*" for anything:
  [
    {"name": "sand-ocean-n",
     "tile": "SAND_OCEAN_N",
     "mask": ["*  OCEAN  *",
              "*  SAND   *",
              "*  *      *"]},
    ...
  ]

Cells past the edge of the map copy the nearest in-bounds cell, so the map
border never draws an edge on its own.
"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import numpy as np

from terrain import Terrain
from tile import Tile
from tilemap import Raster, Tilemap

MASKS_JSON = Path(__file__).with_name("masks.json")
ANY = "*"
NOT = "!"


class MaskConfig(TypedDict):
    name: str
    tile: str
    mask: list[str]


@dataclass(frozen=True)
class Mask:
    name: str
    tile: Tile
    cells: dict[tuple[int, int], frozenset[Terrain]]
    """The terrains allowed at each (row, col) of the 3x3 window; "*" entries are left out."""

    def matches(self, window: Raster) -> bool:
        return all(window[pos] in allowed for pos, allowed in self.cells.items())


def load_masks(path: Path = MASKS_JSON) -> list[Mask]:
    """Read the mask config, failing on bad shapes or unknown names."""
    configs: list[MaskConfig] = json.loads(path.read_text())
    problems: list[str] = []
    masks = [
        mask
        for index, config in enumerate(configs)
        if (mask := _parse_mask(f"mask {index}", config, problems)) is not None
    ]
    seen: set[str] = set()
    for mask in masks:
        if mask.name in seen:
            problems.append(f"duplicate mask name {mask.name}")
        seen.add(mask.name)
    if problems:
        raise ValueError(f"{path}:\n  " + "\n  ".join(problems))
    return masks


def _parse_mask(where: str, config: MaskConfig, problems: list[str]) -> Mask | None:
    """Parse one mask, appending anything wrong with it to problems."""
    name, tile, grid = config.get("name"), config.get("tile"), config.get("mask")
    if not isinstance(name, str) or not name:
        problems.append(f"{where}: missing name")
        return None
    where = f"{where} ({name})"
    if tile not in Tile.__members__:
        problems.append(f"{where}: unknown tile {tile}")
        return None
    rows = [row.split() if isinstance(row, str) else [] for row in grid] if isinstance(grid, list) else []
    if len(rows) != 3 or any(len(row) != 3 for row in rows):
        problems.append(f"{where}: mask must be 3x3")
        return None
    cells: dict[tuple[int, int], frozenset[Terrain]] = {}
    for pos in np.ndindex(3, 3):
        entry = rows[pos[0]][pos[1]]
        if entry == ANY:
            continue
        terrain_name = entry.removeprefix(NOT)
        if terrain_name not in Terrain.__members__:
            problems.append(f"{where}: unknown terrain {entry}")
            continue
        terrain = Terrain[terrain_name]
        negated = entry.startswith(NOT)
        cells[pos] = frozenset(Terrain) - {terrain} if negated else frozenset({terrain})
    return Mask(name, Tile[tile], cells)


def windows(raster: Raster) -> Iterator[tuple[int, int, Raster]]:
    """Yield (row, col, 3x3 window centred on that cell) for every cell."""
    padded = np.pad(raster, 1, mode="edge")
    for row, col in np.ndindex(raster.shape):
        yield row, col, padded[row : row + 3, col : col + 3]


def pick_mask(masks: Sequence[Mask], window: Raster) -> Mask:
    """The first mask matching the window."""
    for mask in masks:
        if mask.matches(window):
            return mask
    raise ValueError(f"no mask matches window:\n{window}")


def place_tiles(raster: Raster, masks: Sequence[Mask]) -> tuple[Tilemap, list[list[str]]]:
    """Pick every cell's tile from the first mask that matches it.

    Returns the tiles and, on the same grid, the name of the mask that picked each.
    """
    height, width = raster.shape
    tiles: Tilemap = [[Tile.OCEAN] * width for _ in range(height)]
    rules = [[""] * width for _ in range(height)]
    for row, col, window in windows(raster):
        mask = pick_mask(masks, window)
        tiles[row][col] = mask.tile
        rules[row][col] = mask.name
    return tiles, rules
