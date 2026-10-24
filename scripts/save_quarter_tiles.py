"""Save the combined tiles named in a config, each built from quarters of existing tiles.

The config (quarter_tiles.json by default) maps a name for each combined tile
to the tile each of its quarters comes from:
  {
    "OCEAN_CHANNEL_VERTICAL": {
      "top_left": "OCEAN_GRASS_NW_INNER", "top_right": "OCEAN_GRASS_NE_INNER",
      "bottom_left": "OCEAN_GRASS_NW_INNER", "bottom_right": "OCEAN_GRASS_NE_INNER"
    }
  }

Each combined tile is written as <out>/<name>.png.

Usage:
  py scripts/save_quarter_tiles.py [--config quarter_tiles.json] [--out output/tilesets/combined]
"""

import argparse
import json
from pathlib import Path

from quarter_preview import QUARTERS, compose, load_images
from tile import Tile

type Combination = tuple[int, int, int, int]
"""The Tile value each quarter comes from, in QUARTERS order."""

QUARTER_TILES_JSON = Path(__file__).with_name("quarter_tiles.json")
DEFAULT_OUT = Path(__file__).parent / "output" / "tilesets" / "combined"


def load_config(path: Path) -> dict[str, Combination]:
    """Read the combined tiles, failing on unknown names, wrong quarters or clashes."""
    data: dict[str, dict[str, str]] = json.loads(path.read_text())
    config: dict[str, Combination] = {}
    problems: list[str] = []
    for name, quarters in data.items():
        if name in Tile.__members__:
            problems.append(f"{name}: already a tile name")
            continue
        if set(quarters) != set(QUARTERS):
            problems.append(f"{name}: needs exactly the quarters {', '.join(QUARTERS)}")
            continue
        unknown = [source for source in quarters.values() if source not in Tile.__members__]
        if unknown:
            problems.append(f"{name}: unknown tiles {', '.join(unknown)}")
            continue
        combination = tuple(Tile[quarters[quarter]].value for quarter in QUARTERS)
        clash = next((other for other, existing in config.items() if existing == combination), None)
        if clash:
            problems.append(f"{name}: same quarters as {clash}")
            continue
        config[name] = combination
    if problems:
        raise ValueError(f"{path}:\n  " + "\n  ".join(problems))
    return config


def save_images(config: dict[str, Combination], out: Path) -> None:
    images = load_images()
    out.mkdir(parents=True, exist_ok=True)
    for name, combination in config.items():
        compose(combination, images).save(out / f"{name}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=QUARTER_TILES_JSON, help="combined tiles to make")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="directory to write the images to")
    args = parser.parse_args()

    config = load_config(args.config)
    save_images(config, args.out)
    print(f"{len(config)} combined tiles written to {args.out}")


if __name__ == "__main__":
    main()
