"""Classify a raster into a 2D grid of Pokemon map tiles."""

from enum import IntEnum

from rasterio.io import DatasetReader


class Tile(IntEnum):
    GRASS = 0
    WATER = 1
    TREE = 2
    PATH = 3
    BUILDING = 4


def render(dataset: DatasetReader) -> list[list[Tile]]:
    """Turn the raster into a 2D list of Tiles, indexed [row][col]."""
    # TODO: classify each pixel from the raster bands
    return [[Tile.GRASS] * dataset.width for _ in range(dataset.height)]
