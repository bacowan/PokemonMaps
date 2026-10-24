"""Build a tile from quarters of existing tiles, and preview one from the command line.

Each quarter of the result is copied from the same quarter of its source tile.

Usage:
  py scripts/quarter_preview.py TOP_LEFT TOP_RIGHT BOTTOM_LEFT BOTTOM_RIGHT [--scale 8]
"""

import argparse
import json
from collections.abc import Sequence

from PIL import Image

from tile import TILES_JSON, Tile

QUARTERS = ("top_left", "top_right", "bottom_left", "bottom_right")
"""The quarters of a tile, in the order combinations list their sources."""


def load_images() -> dict[int, Image.Image]:
    """Open every tile image tiles.json lists that exists, keyed by Tile value.

    Unlike load_tile_images, this doesn't need every Tile in tiles.json, so a
    combined tile can be saved before its entry is added. Combined tiles are
    skipped until save_quarter_tiles.py has written them, so they can't be
    used as sources before then.
    """
    data: dict[str, str] = json.loads(TILES_JSON.read_text())
    images: dict[int, Image.Image] = {}
    for name, path in data.items():
        path = TILES_JSON.parent / path
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for quarter in QUARTERS:
        parser.add_argument(quarter, choices=Tile.__members__, metavar=quarter.upper())
    parser.add_argument("--scale", type=int, default=8, help="how much to enlarge the preview")
    args = parser.parse_args()

    combination = [Tile[getattr(args, quarter)].value for quarter in QUARTERS]
    image = compose(combination, load_images())
    image.resize((image.width * args.scale, image.height * args.scale), Image.Resampling.NEAREST).show()


if __name__ == "__main__":
    main()
