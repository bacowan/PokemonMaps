"""Save the combined tiles named in a config, each built from quarters of existing tiles.

The config (quarter_tiles.json by default) maps a name for each combined tile
to the tile each of its quarters comes from:
  {
    "OCEAN_CHANNEL_VERTICAL": {
      "top_left": "OCEAN_GRASS_NW_INNER", "top_right": "OCEAN_GRASS_NE_INNER",
      "bottom_left": "OCEAN_GRASS_NW_INNER", "bottom_right": "OCEAN_GRASS_NE_INNER"
    }
  }

Each name must also be a Tile, with tiles.json pointing at its image, which is
written as <out>/<name>.png.

Usage:
  py scripts/save_quarter_tiles.py [--config config/quarter_tiles.json] [--out output/tilesets/combined]
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from tile import TILES_JSON, Tile

type Combination = tuple[int, int, int, int]
"""The Tile value each quarter comes from, in QUARTERS order."""

QUARTER_TILES_JSON = Path(__file__).parent / "config" / "quarter_tiles.json"
DEFAULT_OUT = Path(__file__).parent / "output" / "tilesets" / "combined"
QUARTERS = ("top_left", "top_right", "bottom_left", "bottom_right")
"""The quarters of a tile, in the order combinations list their sources."""


def load_images() -> dict[int, Image.Image]:
    """Open every tile image tiles.json lists that exists, keyed by Tile value.

    Unlike load_tile_images, this doesn't need every Tile in tiles.json, so a
    combined tile can be saved before its entry is added. Combined tiles are
    skipped until they have been written, so they can't be used as sources
    before then.
    """
    data: dict[str, str] = json.loads(TILES_JSON.read_text())
    images: dict[int, Image.Image] = {}
    for name, path in data.items():
        path = Path(__file__).parent / path  # tiles.json paths are relative to scripts/
        if name in Tile.__members__ and path.exists():
            images[Tile[name].value] = Image.open(path).convert("RGB")
    return images


def compose(combination: Sequence[int], images: dict[int, Image.Image]) -> Image.Image:
    """The tile whose quarters come from the tiles in combination, in QUARTERS order."""
    sources = [images[value] for value in combination]
    width, height = sources[0].size
    half_w, half_h = width // 2, height // 2
    result = Image.new("RGB", (width, height))
    for index, source in enumerate(sources):
        box = ((index % 2) * half_w, (index // 2) * half_h)
        quarter = source.crop((box[0], box[1], box[0] + half_w, box[1] + half_h))
        result.paste(quarter, box)
    return result


def load_config(path: Path) -> dict[str, Combination]:
    """Read the combined tiles, failing on unknown names, wrong quarters or clashes."""
    data: dict[str, dict[str, str]] = json.loads(path.read_text())
    config: dict[str, Combination] = {}
    problems: list[str] = []
    for name, quarters in data.items():
        if name not in Tile.__members__:
            problems.append(f"{name}: not a tile name; add it to Tile")
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
