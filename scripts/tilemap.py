"""Types shared by the tilemap code."""

import numpy as np
from numpy.typing import NDArray

from tile import Tile

type Tilemap = list[list[Tile]]
"""A 2D grid of tiles, indexed [row][col]."""

type Raster = NDArray[np.integer]
"""The input raster's band as a 2D array of Terrain values, indexed [row][col]."""
