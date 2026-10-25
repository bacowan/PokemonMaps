"""Generate a Pokemon tile map from a raster map."""

from rasterio.io import DatasetReader

from masks import load_masks, place_tiles
from tilemap import Tilemap


def generate_tilemap(dataset: DatasetReader) -> tuple[Tilemap, list[list[str]]]:
    """Turn the raster into a 2D list of Tiles, indexed [row][col], plus the
    name of the mask rule that picked each tile on the same grid."""
    return place_tiles(dataset.read(1), load_masks())
