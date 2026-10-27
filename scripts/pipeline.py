"""The pipeline turning a raster map into a Pokemon tile map.

Stages, in order:
  autotile - pick each cell's tile from its 3x3 neighbourhood (see masks.py)
"""

from rasterio.io import DatasetReader

from masks import autotile, load_masks
from tilemap import Tilemap


def build_map(dataset: DatasetReader) -> tuple[Tilemap, list[list[str]]]:
    """Run the raster through every stage, returning a 2D list of Tiles,
    indexed [row][col], plus the name of the mask rule that picked each tile
    on the same grid."""
    return autotile(dataset.read(1), load_masks())
