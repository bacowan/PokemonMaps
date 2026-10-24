"""The set of tiles a Pokemon tile map is made of."""

import json
from enum import IntEnum
from pathlib import Path

TILES_JSON = Path(__file__).with_name("tiles.json")


class Tile(IntEnum):
    OCEAN = 0
    GRASS = 1
    GRASS_OCEAN_N = 2
    OCEAN_GRASS_N = 3
    OCEAN_GRASS_E = 4
    OCEAN_GRASS_E_OUTER = 5
    OCEAN_GRASS_W = 6
    OCEAN_GRASS_W_OUTER = 7
    OCEAN_GRASS_NW_INNER = 8
    OCEAN_GRASS_NE_INNER = 9
    OCEAN_GRASS_NW_OUTER = 10
    OCEAN_GRASS_NE_OUTER = 11
    SAND = 12
    SAND_GRASS_N = 13
    SAND_GRASS_S = 14
    SAND_GRASS_W = 15
    SAND_GRASS_E = 16
    SAND_GRASS_NW = 17
    SAND_GRASS_NE = 18
    SAND_GRASS_SW = 19
    SAND_GRASS_SE = 20
    SAND_OCEAN_N = 21
    SAND_OCEAN_S = 22
    SAND_OCEAN_W = 23
    SAND_OCEAN_E = 24
    SAND_OCEAN_NW = 25
    SAND_OCEAN_NE = 26
    SAND_OCEAN_SW = 27
    SAND_OCEAN_SE = 28


def load_tile_images(path: Path = TILES_JSON) -> dict[Tile, Path]:
    """Read the tile -> image mapping, failing unless its keys match Tile exactly."""
    data: dict[str, str] = json.loads(path.read_text())
    missing = [tile.name for tile in Tile if tile.name not in data]
    extra = [name for name in data if name not in Tile.__members__]
    problems = []
    if missing:
        problems.append(f"missing tiles: {', '.join(missing)}")
    if extra:
        problems.append(f"unknown tiles: {', '.join(extra)}")
    if problems:
        raise ValueError(f"{path}: {'; '.join(problems)}")
    return {tile: Path(data[tile.name]) for tile in Tile}
