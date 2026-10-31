"""Picking each tile by matching its cell's 3x3 neighbourhood against masks.

The config (masks.json by default) is a list of masks, tried in order for every
cell; the first match wins. Each mask has a unique name (shown as "rule" in the
frontend's debug tooltip), the Tile to use and a grid laid out as on the map
(first row above the cell, centre the cell itself), one space-separated string
per row. The grid is usually 3x3, but can be any odd height and width (e.g.
3x9) when a rule needs to see further. Every entry, centre included, is the
Terrain that cell must be, "!" and a Terrain for anything but that one, or "*"
for anything:
  [
    {"name": "sand-ocean-n",
     "tile": "SAND_OCEAN_N",
     "mask": ["*  OCEAN  *",
              "*  SAND   *",
              "*  *      *"]},
    ...
  ]

Instead of a tile, a mask can have "skip_to" and the name of a later mask:
matching then carries on from that mask, skipping the ones in between.

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

MASKS_JSON = Path(__file__).parent.parent / "config" / "masks.json"
ANY = "*"
NOT = "!"


class MaskConfig(TypedDict, total=False):
    name: str
    tile: str
    skip_to: str
    mask: list[str]


@dataclass(frozen=True)
class Mask:
    name: str
    tile: Tile | None
    """None for a mask that skips to another instead."""
    skip_to: int | None
    """The index of the mask matching carries on from, if this one skips."""
    cells: dict[tuple[int, int], frozenset[Terrain]]
    """The terrains allowed at each (row, col) offset from the centre; "*" entries are left out."""

    @property
    def radius(self) -> int:
        """How far from the centre the mask looks, in either direction."""
        return max((max(abs(row), abs(col)) for row, col in self.cells), default=0)

    def matches(self, window: Raster, radius: int) -> bool:
        """Whether a window reaching radius cells from its centre matches."""
        return all(window[radius + row, radius + col] in allowed for (row, col), allowed in self.cells.items())


def load_masks(path: Path = MASKS_JSON) -> list[Mask]:
    """Read the mask config, failing on bad shapes or unknown names."""
    configs: list[MaskConfig] = json.loads(path.read_text())
    problems: list[str] = []
    names = [config.get("name") for config in configs]
    masks = [
        mask
        for index, config in enumerate(configs)
        if (mask := _parse_mask(f"mask {index}", index, config, names, problems)) is not None
    ]
    seen: set[str] = set()
    for mask in masks:
        if mask.name in seen:
            problems.append(f"duplicate mask name {mask.name}")
        seen.add(mask.name)
    if problems:
        raise ValueError(f"{path}:\n  " + "\n  ".join(problems))
    return masks


def _parse_mask(
    where: str, index: int, config: MaskConfig, names: list[str | None], problems: list[str]
) -> Mask | None:
    """Parse one mask, appending anything wrong with it to problems."""
    name, tile, skip_to, grid = config.get("name"), config.get("tile"), config.get("skip_to"), config.get("mask")
    if not isinstance(name, str) or not name:
        problems.append(f"{where}: missing name")
        return None
    where = f"{where} ({name})"
    if (tile is None) == (skip_to is None):
        problems.append(f"{where}: needs a tile or a skip_to, not both")
        return None
    if tile is not None and tile not in Tile.__members__:
        problems.append(f"{where}: unknown tile {tile}")
        return None
    target = names.index(skip_to) if skip_to in names else None
    if skip_to is not None and (target is None or target <= index):
        problems.append(f"{where}: skip_to {skip_to} must name a later mask")
        return None
    rows = [row.split() if isinstance(row, str) else [] for row in grid] if isinstance(grid, list) else []
    height, width = len(rows), len(rows[0]) if rows else 0
    if height % 2 == 0 or width % 2 == 0 or any(len(row) != width for row in rows):
        problems.append(f"{where}: mask must be a grid of odd height and width")
        return None
    cells: dict[tuple[int, int], frozenset[Terrain]] = {}
    for row, col in np.ndindex(height, width):
        entry = rows[row][col]
        if entry == ANY:
            continue
        terrain_name = entry.removeprefix(NOT)
        if terrain_name not in Terrain.__members__:
            problems.append(f"{where}: unknown terrain {entry}")
            continue
        terrain = Terrain[terrain_name]
        negated = entry.startswith(NOT)
        offset = (row - height // 2, col - width // 2)
        cells[offset] = frozenset(Terrain) - {terrain} if negated else frozenset({terrain})
    # The pickiest cells first, so a mask that doesn't match fails fast.
    cells = dict(sorted(cells.items(), key=lambda item: len(item[1])))
    return Mask(name, Tile[tile] if tile is not None else None, target, cells)


def windows(raster: Raster, radius: int) -> Iterator[tuple[int, int, Raster]]:
    """Yield (row, col, window reaching radius cells from that cell) for every cell."""
    size = 2 * radius + 1
    padded = np.pad(raster, radius, mode="edge")
    for row, col in np.ndindex(raster.shape):
        yield row, col, padded[row : row + size, col : col + size]


def pick_mask(masks: Sequence[Mask], window: Raster, radius: int) -> Mask:
    """The first mask matching the window, following any skips."""
    index = 0
    while index < len(masks):
        mask = masks[index]
        if not mask.matches(window, radius):
            index += 1
        elif mask.skip_to is not None:
            index = mask.skip_to
        else:
            return mask
    raise ValueError(f"no mask matches window:\n{window}")


def autotile(raster: Raster, masks: Sequence[Mask]) -> tuple[Tilemap, list[list[str]]]:
    """Pick every cell's tile from the first mask that matches it.

    Returns the tiles and, on the same grid, the name of the mask that picked each.
    """
    height, width = raster.shape
    radius = max((mask.radius for mask in masks), default=0)
    tiles: Tilemap = [[Tile.OCEAN] * width for _ in range(height)]
    rules = [[""] * width for _ in range(height)]
    for row, col, window in windows(raster, radius):
        mask = pick_mask(masks, window, radius)
        assert mask.tile is not None
        tiles[row][col] = mask.tile
        rules[row][col] = mask.name
    return tiles, rules
