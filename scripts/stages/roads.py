"""Drawing road lines (e.g. a GeoPackage exported from QGIS) onto the raster.

The lines are moved onto the raster's pixel grid, then go through these
substages, in order:
  merge    - merge lines running within merge.distance tiles of one another
             into a single centreline
  simplify - drop vertices the line can do without, keeping it within
             simplify.tolerance tiles of where it was
  steps    - draw each line as a staircase of horizontal and vertical runs
             between its vertices (manhattan routing), one tile thick, with
             as few steps as keep it within steps.max_deviation tiles of the
             line, every run at least steps.min_straight_length tiles long
             where possible (this wins over max_deviation)
The config (roads.json by default) looks like:
  {"merge": {"distance": 3},
   "simplify": {"tolerance": 2},
   "steps": {"min_straight_length": 15, "max_deviation": 4}}

The roads are placed on the raster's own pixel grid, so they need to be in the
raster's CRS; reproject them first if they aren't.
"""

import json
import math
from itertools import pairwise
from pathlib import Path
from typing import TypedDict

import numpy as np
import shapely
from numpy.typing import NDArray
from pyogrio.raw import read
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.io import DatasetReader
from rasterio.transform import Affine
from skimage.morphology import skeletonize

from terrain import Terrain
from tilemap import Raster

ROADS_JSON = Path(__file__).parent.parent / "config" / "roads.json"
# TODO: decide what a road cell becomes (e.g. a new Terrain.ROAD, which will
# also need masks and tiles before autotile can handle it).
ROAD_TERRAIN = Terrain.SAND
MERGE_RESOLUTION = 4
"""Pixels per tile on the grid roads are merged on."""

type Cell = tuple[int, int]
"""A (row, col) on the raster's grid."""

type Point = tuple[float, float]
"""An (x, y) in pixel space: x is the column and y the row, in tiles."""


class MergeConfig(TypedDict):
    distance: float


class SimplifyConfig(TypedDict):
    tolerance: float


class StepsConfig(TypedDict):
    min_straight_length: int
    max_deviation: float


class RoadConfig(TypedDict):
    merge: MergeConfig
    simplify: SimplifyConfig
    steps: StepsConfig


def load_road_config(path: Path = ROADS_JSON) -> RoadConfig:
    """Read the road config, failing on missing or bad values."""
    config: RoadConfig = json.loads(path.read_text())
    checks = [
        ("merge", "distance", float, 0),
        ("simplify", "tolerance", float, 0),
        ("steps", "min_straight_length", int, 1),
        ("steps", "max_deviation", float, 0),
    ]
    problems: list[str] = []
    for section, key, kind, minimum in checks:
        value = config.get(section, {}).get(key)
        valid = isinstance(value, int) or (kind is float and isinstance(value, float))
        if not valid or isinstance(value, bool) or value < minimum:
            problems.append(f"{section}.{key} must be a {kind.__name__} of at least {minimum}")
    if problems:
        raise ValueError(f"{path}:\n  " + "\n  ".join(problems))
    return config


def road_lines(dataset: DatasetReader, roads_path: Path) -> list[shapely.LineString]:
    """The roads as lines in the dataset's pixel space (see Point)."""
    meta, _, wkb, _ = read(roads_path, columns=[])
    roads_crs = CRS.from_user_input(meta["crs"]) if meta["crs"] else None
    if roads_crs != dataset.crs:
        raise ValueError(f"{roads_path} is in {roads_crs}, but the raster is in {dataset.crs}")
    geoms = shapely.from_wkb(wkb)
    to_pixels = ~dataset.transform
    lines: list[shapely.LineString] = []
    for part in shapely.get_parts(geoms[~shapely.is_missing(geoms)]):
        if not isinstance(part, shapely.LineString):
            raise ValueError(f"{roads_path}: roads must be lines, found a {part.geom_type}")
        if not part.is_empty:
            lines.append(shapely.transform(part, lambda xy: np.column_stack(to_pixels * xy.T)))
    return lines


def add_roads(raster: Raster, lines: list[shapely.LineString], config: RoadConfig) -> Raster:
    """A copy of the raster with every road drawn on; the input is left as is."""
    lines = merge_lines(lines, config["merge"]["distance"])
    lines = simplify_lines(lines, config["simplify"]["tolerance"])
    roads = draw_steps(lines, raster.shape, config["steps"])
    raster = raster.copy()
    raster[roads] = ROAD_TERRAIN
    return raster


# merge


def merge_lines(lines: list[shapely.LineString], distance: float) -> list[shapely.LineString]:
    """The lines with any roads running within distance of one another merged
    into a single centreline, split only where roads meet.

    Each line is widened to distance and the result unioned, so nearby roads
    become one shape; that is drawn on a fine grid, thinned to its 1 pixel
    wide skeleton and traced back into lines. Stubs shorter than distance
    hanging off a junction are thinning leftovers, so they are dropped.
    """
    if distance <= 0 or not lines:
        return _line_parts(shapely.line_merge(shapely.unary_union(lines)))
    shape = shapely.unary_union(shapely.buffer(lines, distance / 2))
    min_x, min_y, max_x, max_y = shape.bounds
    origin_x, origin_y = math.floor(min_x) - 1, math.floor(min_y) - 1
    width = math.ceil((max_x - origin_x + 1) * MERGE_RESOLUTION)
    height = math.ceil((max_y - origin_y + 1) * MERGE_RESOLUTION)
    to_tiles = Affine(1 / MERGE_RESOLUTION, 0, origin_x, 0, 1 / MERGE_RESOLUTION, origin_y)
    # all_touched, so a shape thinner than a pixel doesn't break up.
    mask = rasterize([shape], out_shape=(height, width), transform=to_tiles, all_touched=True, dtype=np.uint8)
    paths = _skeleton_paths(skeletonize(mask.astype(np.bool_)), distance * MERGE_RESOLUTION)
    traced = [
        shapely.LineString([to_tiles * (col + 0.5, row + 0.5) for row, col in path]) for path in paths
    ]
    return _line_parts(shapely.line_merge(shapely.MultiLineString(traced)))


def _skeleton_paths(skeleton: NDArray[np.bool_], min_spur: float) -> list[list[Cell]]:
    """The skeleton's pixels traced into paths running between its ends and
    junctions (or round a loop), leaving out stubs shorter than min_spur
    pixels running from an end to a junction."""
    pixels = {(int(row), int(col)) for row, col in np.argwhere(skeleton)}
    neighbours = {pixel: _skeleton_neighbours(pixels, pixel) for pixel in sorted(pixels)}
    seen: set[frozenset[Cell]] = set()

    def walk(start: Cell, step: Cell) -> list[Cell]:
        path = [start, step]
        seen.add(frozenset(path))
        while len(neighbours[path[-1]]) == 2:
            after = next(pixel for pixel in neighbours[path[-1]] if pixel != path[-2])
            if frozenset((path[-1], after)) in seen:
                break
            seen.add(frozenset((path[-1], after)))
            path.append(after)
        return path

    paths: list[list[Cell]] = []
    # Ends and junctions first, then whatever is left: loops with neither.
    starts = sorted(neighbours, key=lambda pixel: len(neighbours[pixel]) == 2)
    for start in starts:
        for step in neighbours[start]:
            if frozenset((start, step)) not in seen:
                paths.append(walk(start, step))
    return [path for path in paths if not _is_spur(path, neighbours, min_spur)]


def _skeleton_neighbours(pixels: set[Cell], pixel: Cell) -> list[Cell]:
    """The skeleton pixels next to pixel. A diagonal one only counts when the
    two don't share a side neighbour, so a corner isn't read as a junction."""
    row, col = pixel
    sides = [(row + d_row, col + d_col) for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1))]
    diagonals = [
        (row + d_row, col + d_col)
        for d_row, d_col in ((-1, -1), (-1, 1), (1, -1), (1, 1))
        if (row + d_row, col) not in pixels and (row, col + d_col) not in pixels
    ]
    return [neighbour for neighbour in sides + diagonals if neighbour in pixels]


def _is_spur(path: list[Cell], neighbours: dict[Cell, list[Cell]], min_spur: float) -> bool:
    """Whether the path runs from an end to a junction and is shorter than min_spur."""
    ends = sorted((len(neighbours[path[0]]), len(neighbours[path[-1]])))
    return ends[0] == 1 and ends[1] >= 3 and shapely.LineString(path).length < min_spur


def _line_parts(geometry: shapely.Geometry) -> list[shapely.LineString]:
    return [part for part in shapely.get_parts(geometry) if isinstance(part, shapely.LineString)]


# simplify


def simplify_lines(lines: list[shapely.LineString], tolerance: float) -> list[shapely.LineString]:
    """The lines with as few vertices as keep them within tolerance of where
    they were (Douglas-Peucker). Endpoints are kept, so roads stay joined."""
    if tolerance <= 0:
        return lines
    return list(shapely.simplify(lines, tolerance))


# steps


def draw_steps(
    lines: list[shapely.LineString], shape: tuple[int, ...], config: StepsConfig
) -> NDArray[np.bool_]:
    """Which cells of a grid of the given shape the lines' staircases pass through."""
    roads = np.zeros(shape, dtype=np.bool_)
    for line in lines:
        cells = [(math.floor(y), math.floor(x)) for x, y in shapely.get_coordinates(line)]
        corners = route(cells, config["min_straight_length"], config["max_deviation"])
        _draw_segment(roads, corners[0], corners[0])
        for start, end in pairwise(corners):
            _draw_segment(roads, start, end)
    return roads


def route(line: list[Cell], min_straight_length: int, max_deviation: float) -> list[Cell]:
    """The corners of a manhattan route through the line's vertices, each
    consecutive pair joined by a horizontal or vertical run.

    Offsets too small for a run are carried into the next leg, so runs only
    fall short of min_straight_length on the leg into the line's end, which is
    always reached exactly so roads sharing an endpoint stay connected.
    """
    corners = [line[0]]
    for index, target in enumerate(line[1:], start=1):
        exact = index == len(line) - 1
        corners += _staircase(corners[-1], target, min_straight_length, max_deviation, exact)
    return corners


def _staircase(
    start: Cell, target: Cell, min_straight_length: int, max_deviation: float, exact: bool
) -> list[Cell]:
    """The corners after start of a staircase towards target, ending at the
    last corner. Unless exact, an axis offset by less than min_straight_length
    is left for the next leg, so the staircase may stop short of target.

    The staircase is the one with the fewest runs, all at least
    min_straight_length long, that stays within max_deviation of the straight
    line to target; if none does, the closest one with long enough runs.
    """
    row, col = start
    d_row, d_col = target[0] - row, target[1] - col
    if not exact:
        d_row = d_row if abs(d_row) >= min_straight_length else 0
        d_col = d_col if abs(d_col) >= min_straight_length else 0
    if d_row == 0 or d_col == 0:
        return [(row + d_row, col + d_col)] if d_row or d_col else []
    # Fewest runs first: an L, a Z, two steps, two steps centred, ...
    candidates: list[list[Cell]] = []
    for steps in range(1, max(1, min(abs(d_row), abs(d_col)) // min_straight_length) + 1):
        for centred in (False, True):
            corners = _stairs(d_row, d_col, steps, centred)
            if all(_length(a, b) >= min_straight_length for a, b in pairwise([(0, 0), *corners])):
                candidates.append(corners)
    if not candidates:
        # Only on an exact leg too short for any run to be long enough.
        candidates = [_stairs(d_row, d_col, 1, centred=False)]
    within = [corners for corners in candidates if _deviation(corners, d_row, d_col) <= max_deviation]
    best = within[0] if within else min(candidates, key=lambda corners: _deviation(corners, d_row, d_col))
    return [(row + corner_row, col + corner_col) for corner_row, corner_col in best]


def _stairs(d_row: int, d_col: int, steps: int, centred: bool) -> list[Cell]:
    """The corners, relative to the start, of a staircase of the given number
    of steps to (d_row, d_col), each a run along the longer axis then one
    along the shorter. Centred, the first run along the longer axis is split
    between the start and the end, so the staircase straddles the straight
    line instead of sitting to one side of it."""
    rows_major = abs(d_row) > abs(d_col)
    major, minor = (d_row, d_col) if rows_major else (d_col, d_row)
    corners: list[tuple[int, int]] = []
    for step in range(steps):
        along = _cut(major, 2 * steps, 2 * step + 1) if centred else _cut(major, steps, step + 1)
        corners += [(along, _cut(minor, steps, step)), (along, _cut(minor, steps, step + 1))]
    if centred:
        corners.append((major, minor))
    return [(along, across) if rows_major else (across, along) for along, across in corners]


def _cut(total: int, parts: int, index: int) -> int:
    """Where the index'th of parts near-equal pieces of total ends."""
    return int(np.sign(total)) * (abs(total) * index // parts)


def _length(start: Cell, end: Cell) -> int:
    """The length of a horizontal or vertical run, in tiles."""
    return abs(end[0] - start[0]) + abs(end[1] - start[1])


def _deviation(corners: list[Cell], d_row: int, d_col: int) -> float:
    """How far, at most, the staircase strays from the straight line from the
    start to (d_row, d_col), in tiles."""
    return max(abs(row * d_col - col * d_row) / math.hypot(d_row, d_col) for row, col in corners)


def _draw_segment(roads: NDArray[np.bool_], start: Cell, end: Cell) -> None:
    """Mark the cells of a horizontal or vertical run, clipped to the grid."""
    rows = slice(max(min(start[0], end[0]), 0), max(max(start[0], end[0]) + 1, 0))
    cols = slice(max(min(start[1], end[1]), 0), max(max(start[1], end[1]) + 1, 0))
    roads[rows, cols] = True
