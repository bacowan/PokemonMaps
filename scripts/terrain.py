"""The values a pixel in the input raster can take."""

from enum import IntEnum


class Terrain(IntEnum):
    OCEAN = 0
    LAND = 1
    SAND = 2
    STREET = 3
    HIGHWAY = 4
