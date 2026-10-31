"""Convert a raster map (GeoTIFF) into a Pokemon-style map.

The raster is turned into a 2D grid of Tile values, one per raster pixel,
which is then written next to each other as:
  <out>.json  - grid size, tile legend and source georeferencing
  <out>.bin   - the tile grid, one uint8 per tile, row-major
  <out>.tif   - the tile grid as a single-band GeoTIFF on the source's grid
  <out>.cells.json - per-cell metadata, one [row][col] grid per field:
                     source - the raster value the tile was made from, after
                              the stages before autotile (e.g. roads)
                     rule   - the name of the masks.json rule that picked the tile

Settings are read from scripts/config.toml (copy config.sample.toml to make
one); relative paths in it are resolved from the config file's directory.

Usage:
  py -m pip install -r requirements.txt
  py scripts/raster_to_pokemon.py [--config path/to/config.toml]
"""

import argparse
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.profiles import Profile

from pipeline import build_map
from tile import Tile
from tilemap import Raster

CONFIG_TOML = Path(__file__).parent / "config.toml"


@dataclass(frozen=True)
class Config:
    raster: Path  # input .tif raster
    roads: Path  # road lines (e.g. .gpkg), in the same CRS as the raster
    highways: Path  # highway lines, same format as roads
    output: Path  # output path, without extension


def load_config(path: Path) -> Config:
    data: dict[str, str] = tomllib.loads(path.read_text())
    missing = [key for key in ("raster", "roads", "highways", "output") if key not in data]
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(missing)}")
    base = path.parent
    return Config(
        raster=base / data["raster"],
        roads=base / data["roads"],
        highways=base / data["highways"],
        output=base / data["output"],
    )


def save(
    tiles: list[list[Tile]], rules: list[list[str]], source: Raster, profile: Profile, out: Path
) -> None:
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

    cells = {"source": source.tolist(), "rule": rules}
    out.with_suffix(".cells.json").write_text(json.dumps(cells, separators=(",", ":")))

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
    parser.add_argument("--config", type=Path, default=CONFIG_TOML, help="settings file (default: scripts/config.toml)")
    args = parser.parse_args()

    if not args.config.is_file():
        parser.error(f"config file not found: {args.config} (copy config.sample.toml to make one)")
    try:
        config = load_config(args.config)
    except (ValueError, tomllib.TOMLDecodeError) as e:
        parser.error(str(e))

    if not config.raster.is_file():
        parser.error(f"input file not found: {config.raster}")
    if not config.roads.is_file():
        parser.error(f"roads file not found: {config.roads}")
    if not config.highways.is_file():
        parser.error(f"highways file not found: {config.highways}")

    with rasterio.open(config.raster) as dataset:
        tiles, rules, source = build_map(dataset, config.roads, config.highways)
        profile = dataset.profile

    save(tiles, rules, source, profile, config.output)


if __name__ == "__main__":
    main()
