"""Drawing road lines (e.g. a GeoPackage exported from QGIS) onto the raster.

The roads are burned onto the raster's own pixel grid, so they need to be in
the raster's CRS; reproject them first if they aren't.
"""

from pathlib import Path

import numpy as np
import shapely
from numpy.typing import NDArray
from pyogrio.raw import read
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.io import DatasetReader

from tilemap import Raster


def road_cells(dataset: DatasetReader, roads_path: Path) -> NDArray[np.bool_]:
    """Which cells of the dataset's grid a road passes through, indexed [row][col]."""
    meta, _, wkb, _ = read(roads_path, columns=[])
    roads_crs = CRS.from_user_input(meta["crs"]) if meta["crs"] else None
    if roads_crs != dataset.crs:
        raise ValueError(f"{roads_path} is in {roads_crs}, but the raster is in {dataset.crs}")
    lines = [geom for geom in shapely.from_wkb(wkb) if geom is not None]
    if not lines:
        return np.zeros(dataset.shape, dtype=np.bool_)
    # all_touched, so a line clipping the corner of a cell still marks it and
    # roads stay connected instead of breaking up where they run diagonally.
    burned = rasterize(lines, out_shape=dataset.shape, transform=dataset.transform, all_touched=True, dtype=np.uint8)
    return burned.astype(np.bool_)


def add_roads(raster: Raster, roads: NDArray[np.bool_]) -> Raster:
    """A copy of the raster with the road cells changed; the input is left as is."""
    raster = raster.copy()
    # TODO: decide what a road cell becomes (e.g. a new Terrain.ROAD, which
    # will also need masks and tiles before autotile can handle it).
    return raster
