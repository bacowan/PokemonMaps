"""Generate a Pokemon tile map from a raster map."""

from rasterio.io import DatasetReader

from masks import load_masks, place_tiles
from tilemap import Tilemap


def generate_tilemap(dataset: DatasetReader) -> Tilemap:
    """Turn the raster into a 2D list of Tiles, indexed [row][col]."""
    return place_tiles(dataset.read(1), load_masks())
