"""Convert a raster map (GeoTIFF) into a Pokemon-style map.

The raster is turned into a 2D grid of Tile values, one per raster pixel,
which is then written next to each other as:
  <out>.json  - grid size, tile legend and source georeferencing
  <out>.bin   - the tile grid, one uint8 per tile, row-major
  <out>.tif   - the tile grid as a single-band GeoTIFF on the source's grid

Usage:
  py -m pip install -r requirements.txt
  py scripts/raster_to_pokemon.py <input.tif> <output path>
"""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.profiles import Profile

from map_tiles import generate_tilemap
from tile import Tile


def save(tiles: list[list[Tile]], profile: Profile, out: Path) -> None:
    grid = np.array(tiles, dtype=np.uint8)
    height, width = grid.shape
    out.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "width": width,
        "height": height,
        "tiles": {tile.name: tile.value for tile in Tile},
        "crs": profile["crs"].to_string() if profile.get("crs") else None,
        "transform": list(profile["transform"])[:6],
    }
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))

    out.with_suffix(".bin").write_bytes(grid.tobytes())

    # Only crs and transform come from the source, so each tile sits on the
    # pixel it came from; the rest describes our single band of tile values.
    tif_profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 1,
        "dtype": "uint8",
        "crs": profile.get("crs"),
        "transform": profile["transform"],
    }
    with rasterio.open(out.with_suffix(".tif"), "w", **tif_profile) as dst:
        dst.write(grid, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tif", type=Path, help="input .tif raster")
    parser.add_argument("out", type=Path, help="output path, without extension (e.g. output/map)")
    args = parser.parse_args()

    if not args.tif.is_file():
        parser.error(f"input file not found: {args.tif}")

    with rasterio.open(args.tif) as dataset:
        tiles = generate_tilemap(dataset)
        profile = dataset.profile

    save(tiles, profile, args.out)


if __name__ == "__main__":
    main()
