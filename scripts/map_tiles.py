"""Generate a Pokemon tile map from a raster map."""

from collections.abc import Sequence

from rasterio.io import DatasetReader

from stages.place_land import place_land
from stages.place_sand import place_sand
from tile import Tile
from tilemap import Raster, Stage, Tilemap


def initial_tilemap(raster: Raster) -> Tilemap:
    """An all-ocean tilemap the same size as the raster."""
    height, width = raster.shape
    return [[Tile.OCEAN] * width for _ in range(height)]


STAGES: Sequence[Stage] = [
    place_land,
    place_sand,
]


def run_pipeline(raster: Raster, tiles: Tilemap, stages: Sequence[Stage]) -> Tilemap:
    """Thread the tilemap through each stage in order."""
    for stage in stages:
        tiles = stage(raster, tiles)
    return tiles


def generate_tilemap(dataset: DatasetReader) -> Tilemap:
    """Turn the raster into a 2D list of Tiles, indexed [row][col]."""
    raster = dataset.read(1)
    return run_pipeline(raster, initial_tilemap(raster), STAGES)
