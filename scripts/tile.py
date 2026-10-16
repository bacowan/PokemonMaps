"""The set of tiles a Pokemon tile map is made of."""

import json
from enum import IntEnum
from pathlib import Path

TILES_JSON = Path(__file__).with_name("tiles.json")


class Tile(IntEnum):
    OCEAN_CENTER = 0
    GRASS_CENTER = 1
    GRASS_BELOW_OCEAN = 2
    OCEAN_BELOW_GRASS = 3
    OCEAN_LEFT_OF_GRASS = 4
    OCEAN_LEFT_OF_GRASS_CORNER = 5
    OCEAN_RIGHT_OF_GRASS = 6
    OCEAN_RIGHT_OF_GRASS_CORNER = 7
    OCEAN_BELOW_RIGHT_OF_GRASS = 8
    OCEAN_BELOW_LEFT_OF_GRASS = 9
    OCEAN_BELOW_RIGHT_OF_GRASS_CORNER = 10
    OCEAN_BELOW_LEFT_OF_GRASS_CORNER = 11


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
