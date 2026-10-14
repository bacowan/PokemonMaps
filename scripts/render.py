"""Classify a raster into a 2D grid of Pokemon map tiles."""

import json
from pathlib import Path

from rasterio.io import DatasetReader

from tile import Tile

TILES_JSON = Path(__file__).with_name("tiles.json")


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


def render(dataset: DatasetReader) -> list[list[Tile]]:
    """Turn the raster into a 2D list of Tiles, indexed [row][col]."""
    # TODO: classify each pixel from the raster bands
    return [[Tile.GRASS_CENTER] * dataset.width for _ in range(dataset.height)]
