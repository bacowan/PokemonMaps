"""The set of tiles a Pokemon tile map is made of."""

import json
from enum import IntEnum, auto, unique
from pathlib import Path

TILES_JSON = Path(__file__).with_name("tiles.json")


@unique
class Tile(IntEnum):
    OCEAN = auto()
    GRASS = auto()
    GRASS_OCEAN_N = auto()
    OCEAN_GRASS_N = auto()
    OCEAN_GRASS_E = auto()
    OCEAN_GRASS_E_OUTER = auto()
    OCEAN_GRASS_W = auto()
    OCEAN_GRASS_W_OUTER = auto()
    OCEAN_GRASS_NW_INNER = auto()
    OCEAN_GRASS_NE_INNER = auto()
    OCEAN_GRASS_NW_OUTER = auto()
    OCEAN_GRASS_NE_OUTER = auto()
    SAND = auto()
    SAND_GRASS_N = auto()
    SAND_GRASS_S = auto()
    SAND_GRASS_W = auto()
    SAND_GRASS_E = auto()
    SAND_GRASS_NW = auto()
    SAND_GRASS_NE = auto()
    SAND_GRASS_SW = auto()
    SAND_GRASS_SE = auto()
    SAND_OCEAN_N = auto()
    SAND_OCEAN_S = auto()
    SAND_OCEAN_W = auto()
    SAND_OCEAN_E = auto()
    SAND_OCEAN_NW = auto()
    SAND_OCEAN_NE = auto()
    SAND_OCEAN_SW = auto()
    SAND_OCEAN_SE = auto()
    SAND_OCEAN_SW_INNER = auto()
    SAND_OCEAN_SE_INNER = auto()
    # Combined from quarters of other tiles by save_quarter_tiles.py.
    OCEAN_CHANNEL_VERTICAL = auto()
    OCEAN_CHANNEL_VERTICAL_NW_CORNER = auto()
    SAND_OCEAN_W_GRASS_NW = auto()
    OCEAN_CHANNEL_VERTICAL_NW_OUTER_CORNER = auto()
    OCEAN_SAND_NW_GRASS_E = auto()


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
