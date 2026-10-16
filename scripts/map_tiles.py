"""Generate a Pokemon tile map from a raster map."""

from rasterio.io import DatasetReader

from tile import Tile


def generate_tilemap(dataset: DatasetReader) -> list[list[Tile]]:
    """Turn the raster into a 2D list of Tiles, indexed [row][col]."""
    # TODO: build tiles from the raster bands
    return [[Tile.GRASS_CENTER] * dataset.width for _ in range(dataset.height)]
