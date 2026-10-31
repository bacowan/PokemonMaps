"""The pipeline turning a raster map into a Pokemon tile map.

Stages, in order:
  roads    - draw road lines onto a copy of the raster (see stages/roads.py)
  highways - the same, with the highway config, drawn over the roads
  autotile - pick each cell's tile from its 3x3 neighbourhood (see stages/masks.py)
"""

from pathlib import Path

from rasterio.io import DatasetReader

from stages.masks import autotile, load_masks
from stages.roads import HIGHWAYS_JSON, add_roads, load_road_config, road_lines
from terrain import Terrain
from tilemap import Raster, Tilemap

# TODO: draw roads as Terrain.STREET once it has masks and tiles for autotile.
ROAD_TERRAIN = Terrain.SAND


def build_map(
    dataset: DatasetReader, roads_path: Path, highways_path: Path
) -> tuple[Tilemap, list[list[str]], Raster]:
    """Run the raster through every stage, returning a 2D list of Tiles,
    indexed [row][col], the name of the mask rule that picked each tile on the
    same grid, and the raster as autotile saw it (after every earlier stage)."""
    raster = add_roads(dataset.read(1), road_lines(dataset, roads_path), load_road_config(), ROAD_TERRAIN)
    # Second, so highways win where they cross roads.
    highways = road_lines(dataset, highways_path)
    raster = add_roads(raster, highways, load_road_config(HIGHWAYS_JSON), Terrain.HIGHWAY)
    tiles, rules = autotile(raster, load_masks())
    return tiles, rules, raster
