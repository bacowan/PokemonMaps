"""The set of tiles a Pokemon tile map is made of."""

import json
from enum import IntEnum, auto, unique
from pathlib import Path

TILES_JSON = Path(__file__).parent / "config" / "tiles.json"


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
    OCEAN_CHANNEL_VERTICAL_SAND_RIGHT = auto()
    OCEAN_CHANNEL_VERTICAL_SAND_RIGHT_CORNER_NE = auto()
    OCEAN_CHANNEL_VERTICAL_SAND_RIGHT_CORNER_SE = auto()
    OCEAN_GRASS_NE_OUTER_SAND_NW_OUTER = auto()
    SAND_OCEAN_NE_GRASS_W = auto()
    OCEAN_GRASS_NW_NE_OUTER = auto()
    OCEAN_CHANNEL_VERTICAL_NE_OUTER_CORNER = auto()
    OCEAN_CHANNEL_VERTICAL_TOP = auto()
    # The highway: Route 110's Cycling Road (secondary/mauville), drawn 3 tiles wide.
    HIGHWAY = auto()
    HIGHWAY_N = auto()
    HIGHWAY_S = auto()
    HIGHWAY_W = auto()
    HIGHWAY_E = auto()
    HIGHWAY_NW = auto()
    HIGHWAY_NE = auto()
    HIGHWAY_SW = auto()
    HIGHWAY_SE = auto()
    HIGHWAY_NW_INNER = auto()
    HIGHWAY_NE_INNER = auto()
    HIGHWAY_SW_INNER = auto()
    HIGHWAY_SE_INNER = auto()
    HIGHWAY_S_BRANCH_SW = auto()
    HIGHWAY_S_BRANCH_SE = auto()
    HIGHWAY_FACE = auto()
    HIGHWAY_JOIN_NE = auto()
    HIGHWAY_JOIN_NW = auto()
    HIGHWAY_JOIN_SE = auto()
    HIGHWAY_JOIN_SW = auto()
    OCEAN_HIGHWAY_S = auto()
    GRASS_HIGHWAY_S = auto()
    OCEAN_HIGHWAY_S_W_END = auto()
    GRASS_HIGHWAY_S_W_END = auto()
    OCEAN_HIGHWAY_S_E_END = auto()
    GRASS_HIGHWAY_S_E_END = auto()
    OCEAN_HIGHWAY_N_W_END = auto()
    GRASS_HIGHWAY_N_W_END = auto()
    OCEAN_HIGHWAY_N_E_END = auto()
    GRASS_HIGHWAY_N_E_END = auto()
    OCEAN_HIGHWAY_E = auto()
    GRASS_HIGHWAY_E = auto()
    OCEAN_HIGHWAY_E_N_END = auto()
    GRASS_HIGHWAY_E_N_END = auto()
    OCEAN_HIGHWAY_E_S_END = auto()
    GRASS_HIGHWAY_E_S_END = auto()
    OCEAN_HIGHWAY_W = auto()
    GRASS_HIGHWAY_W = auto()
    OCEAN_HIGHWAY_W_N_END = auto()
    GRASS_HIGHWAY_W_N_END = auto()
    OCEAN_HIGHWAY_W_S_END = auto()
    GRASS_HIGHWAY_W_S_END = auto()
    OCEAN_HIGHWAY_SE_OUTER = auto()
    GRASS_HIGHWAY_SE_OUTER = auto()
    OCEAN_HIGHWAY_SW_OUTER = auto()
    GRASS_HIGHWAY_SW_OUTER = auto()
    OCEAN_HIGHWAY_NE_OUTER = auto()
    GRASS_HIGHWAY_NE_OUTER = auto()
    OCEAN_HIGHWAY_NW_OUTER = auto()
    GRASS_HIGHWAY_NW_OUTER = auto()
    GRASS_HIGHWAY_E_S_END_POST = auto()
    GRASS_HIGHWAY_W_S_END_POST = auto()


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
