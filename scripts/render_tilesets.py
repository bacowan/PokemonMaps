"""Download the pokeemerald tilesets and render them as coloured images.

tiles.png in pokeemerald only stores 4bpp colour indices; which of the 16
palettes a tile uses is decided per-tile by metatiles.bin. So for each tileset
this renders every metatile (16x16 block) with its proper palette, which is what
the game actually draws.

Secondary tilesets borrow tiles and palettes 0-5 from a primary tileset, so each
secondary is paired with the primary it is most commonly used with in
data/layouts/layouts.json.

Outputs, per tileset, in <out>/<path under data/tilesets>/:
  metatiles.png      - all metatiles, both layers composited
  metatiles/XXX.png  - (with --split) each metatile as its own 16x16 image,
                       named by its metatile ID in hex as the game numbers them
                       (secondary tilesets start at 200)
  tiles_palNN.png    - (with --tile-sheets) the raw tile sheet in palette NN, for
                       each palette the tileset's metatiles use with its tiles

Usage:
  py -m pip install pillow
  py scripts/render_tilesets.py [--out output/tilesets] [--ref master] [--split] [--tile-sheets]
"""

import argparse
import json
import re
import struct
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

REPO = "pret/pokeemerald"

# From include/fieldmap.h
NUM_TILES_IN_PRIMARY = 512
NUM_PALS_IN_PRIMARY = 6
NUM_METATILES_IN_PRIMARY = 512

TILE = 8
METATILE = 16
METATILES_PER_ROW = 8
TILES_PER_ROW = 16


class Downloader:
    def __init__(self, ref, cache_dir):
        self.base = f"https://raw.githubusercontent.com/{REPO}/{ref}/"
        self.cache_dir = cache_dir / ref

    def fetch(self, path):
        cached = self.cache_dir / path
        if cached.exists():
            return cached.read_bytes()
        with urllib.request.urlopen(self.base + path) as resp:
            data = resp.read()
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
        return data

    def fetch_text(self, path):
        return self.fetch(path).decode("utf-8")


def find_tilesets(dl):
    """Return {symbol: {"tiles": path, "palettes": [paths], "metatiles": path}}.

    Paths are looked up per field because some tilesets (e.g. the secret bases)
    share metatiles but take their tiles and palettes from elsewhere.
    """
    headers = dl.fetch_text("src/data/tilesets/headers.h")
    # Most graphics are in graphics.h, but a few (e.g. General) live in src/graphics.c.
    graphics = dl.fetch_text("src/data/tilesets/graphics.h") + dl.fetch_text("src/graphics.c")
    metatiles = dl.fetch_text("src/data/tilesets/metatiles.h")

    tile_paths = dict(re.findall(r'const u32 (gTilesetTiles_\w+)\[\]\s*=\s*\w+\("([^"]+\.png)"', graphics))
    palette_paths = {
        symbol: re.findall(r'"([^"]+\.pal)"', body)
        for symbol, body in re.findall(r"const u16 (gTilesetPalettes_\w+)\[\]\[16\]\s*=\s*\{(.*?)\};", graphics, re.S)
    }
    metatile_paths = dict(re.findall(r'const u16 (gMetatiles_\w+)\[\]\s*=\s*\w+\("([^"]+\.bin)"', metatiles))

    tilesets = {}
    for symbol, body in re.findall(r"const struct Tileset (gTileset_\w+)\s*=\s*\{(.*?)\};", headers, re.S):
        fields = dict(re.findall(r"\.(\w+)\s*=\s*(\w+)", body))
        try:
            tilesets[symbol] = {
                "tiles": tile_paths[fields["tiles"]],
                "palettes": palette_paths[fields["palettes"]],
                "metatiles": metatile_paths[fields["metatiles"]],
                "secondary": fields.get("isSecondary") == "TRUE",
            }
        except KeyError as e:
            print(f"Skipping {symbol}: couldn't find source for {e}")
    return tilesets


def find_primary_for_secondaries(dl):
    """Return {secondary symbol: primary symbol}, using the most common pairing in layouts."""
    layouts = json.loads(dl.fetch_text("data/layouts/layouts.json"))["layouts"]
    pairings = {}
    for layout in layouts:
        if "secondary_tileset" in layout:
            pairings.setdefault(layout["secondary_tileset"], Counter())[layout["primary_tileset"]] += 1
    return {secondary: counts.most_common(1)[0][0] for secondary, counts in pairings.items()}


def parse_jasc_pal(text):
    lines = text.split()
    if lines[0] != "JASC-PAL":
        raise ValueError("not a JASC palette")
    count = int(lines[2])
    values = list(map(int, lines[3:3 + count * 3]))
    return [tuple(values[i:i + 3]) for i in range(0, len(values), 3)]


class Tileset:
    def __init__(self, dl, sources):
        # e.g. "secondary/secret_base/brown_cave"
        self.name = sources["tiles"].removeprefix("data/tilesets/").rsplit("/", 1)[0]
        self.is_secondary = sources["secondary"]
        self.tiles = self._load_tiles(dl.fetch(sources["tiles"]))
        self.palettes = [parse_jasc_pal(dl.fetch_text(path)) for path in sources["palettes"]]
        raw = dl.fetch(sources["metatiles"])
        self.metatiles = struct.unpack(f"<{len(raw) // 2}H", raw)

    @staticmethod
    def _load_tiles(png_bytes):
        """Return the tile sheet as a list of 8x8 tiles, each a flat list of 64 colour indices."""
        import io
        img = Image.open(io.BytesIO(png_bytes))
        if img.mode == "P":
            pixels = list(img.get_flattened_data())
        else:
            # Greyscale fallback: map brightness onto 16 indices.
            pixels = [round(v * 15 / 255) for v in img.convert("L").get_flattened_data()]
        pixels = [p & 0xF for p in pixels]
        width, height = img.size
        tiles = []
        for ty in range(height // TILE):
            for tx in range(width // TILE):
                tiles.append([pixels[(ty * TILE + y) * width + tx * TILE + x]
                              for y in range(TILE) for x in range(TILE)])
        return tiles


def draw_tile(img, tile, palette, ox, oy, hflip, vflip, transparent):
    px = img.load()
    for y in range(TILE):
        for x in range(TILE):
            index = tile[y * TILE + x]
            if transparent and index == 0:
                continue
            dx = TILE - 1 - x if hflip else x
            dy = TILE - 1 - y if vflip else y
            px[ox + dx, oy + dy] = palette[index]


def combined_graphics(tileset, primary):
    """Return the (tiles, palettes) the game has loaded while `tileset` is in use.

    `primary` is the paired primary (None for primaries). Tile and palette
    indices in metatiles.bin index into these lists.
    """
    if primary is None:
        tiles = tileset.tiles
        palettes = tileset.palettes[:NUM_PALS_IN_PRIMARY]
    else:
        tiles = primary.tiles[:NUM_TILES_IN_PRIMARY]
        tiles = tiles + [[0] * 64] * (NUM_TILES_IN_PRIMARY - len(tiles)) + tileset.tiles
        palettes = primary.palettes[:NUM_PALS_IN_PRIMARY] + tileset.palettes[NUM_PALS_IN_PRIMARY:]
    palettes = palettes + [[(255, 0, 255)] * 16] * (16 - len(palettes))
    return tiles, palettes


def own_tile_palettes(tileset):
    """Return the palette indices `tileset`'s metatiles use with `tileset`'s own tiles.

    Blank or out-of-range tiles are ignored; some metatiles.bin files point those
    at unused palettes, and they look the same in any palette anyway.
    """
    offset = NUM_TILES_IN_PRIMARY if tileset.is_secondary else 0
    used = set()
    for entry in tileset.metatiles:
        tile_index = (entry & 0x3FF) - offset
        if 0 <= tile_index < len(tileset.tiles) and any(tileset.tiles[tile_index]):
            used.add(entry >> 12)
    return sorted(used)


def render_metatile(tileset: Tileset, tiles: list[list[int]], palettes: list[list[tuple[int, int, int]]],
                    m: int) -> Image.Image:
    """Render metatile `m` of `tileset` using the loaded graphics from combined_graphics."""
    blank = [0] * 64
    img = Image.new("RGB", (METATILE, METATILE), palettes[0][0])
    # 8 entries: bottom layer TL, TR, BL, BR, then top layer TL, TR, BL, BR.
    for i, entry in enumerate(tileset.metatiles[m * 8:m * 8 + 8]):
        tile_index = entry & 0x3FF
        tile = tiles[tile_index] if tile_index < len(tiles) else blank
        draw_tile(img, tile, palettes[entry >> 12], (i % 2) * TILE, ((i // 2) % 2) * TILE,
                  hflip=bool(entry & 0x400), vflip=bool(entry & 0x800), transparent=True)
    return img


def render_metatiles(tileset: Tileset, tiles: list[list[int]],
                     palettes: list[list[tuple[int, int, int]]]) -> list[Image.Image]:
    """Render each metatile of `tileset` using the loaded graphics from combined_graphics."""
    return [render_metatile(tileset, tiles, palettes, m) for m in range(len(tileset.metatiles) // 8)]


def metatile_sheet(metatiles: list[Image.Image], backdrop: tuple[int, int, int]) -> Image.Image:
    rows = (len(metatiles) + METATILES_PER_ROW - 1) // METATILES_PER_ROW
    img = Image.new("RGB", (METATILES_PER_ROW * METATILE, rows * METATILE), backdrop)
    for m, metatile in enumerate(metatiles):
        img.paste(metatile, ((m % METATILES_PER_ROW) * METATILE, (m // METATILES_PER_ROW) * METATILE))
    return img


def render_tile_sheet(tileset, palette):
    rows = (len(tileset.tiles) + TILES_PER_ROW - 1) // TILES_PER_ROW
    img = Image.new("RGB", (TILES_PER_ROW * TILE, rows * TILE))
    for i, tile in enumerate(tileset.tiles):
        draw_tile(img, tile, palette, (i % TILES_PER_ROW) * TILE, (i // TILES_PER_ROW) * TILE,
                  hflip=False, vflip=False, transparent=False)
    return img


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("output/tilesets"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/pokeemerald"))
    parser.add_argument("--ref", default="master", help="git branch/tag/commit to download")
    parser.add_argument("--tile-sheets", action="store_true",
                        help="also write the raw tile sheet once per palette it is used with")
    parser.add_argument("--split", action="store_true",
                        help="also write each metatile as its own image")
    args = parser.parse_args()

    dl = Downloader(args.ref, args.cache)
    symbols = find_tilesets(dl)
    pairings = find_primary_for_secondaries(dl)

    print(f"Downloading {len(symbols)} tilesets...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        loaded = dict(zip(symbols, pool.map(lambda path: Tileset(dl, path), symbols.values())))

    for symbol, tileset in loaded.items():
        primary = None
        if tileset.is_secondary:
            primary_symbol = pairings.get(symbol, "gTileset_General")
            primary = loaded[primary_symbol]

        out_dir = args.out / tileset.name
        out_dir.mkdir(parents=True, exist_ok=True)
        tiles, palettes = combined_graphics(tileset, primary)
        metatiles = render_metatiles(tileset, tiles, palettes)
        metatile_sheet(metatiles, palettes[0][0]).save(out_dir / "metatiles.png")
        if args.split:
            split_dir = out_dir / "metatiles"
            split_dir.mkdir(exist_ok=True)
            first_id = NUM_METATILES_IN_PRIMARY if tileset.is_secondary else 0
            for m, metatile in enumerate(metatiles):
                metatile.save(split_dir / f"{first_id + m:03X}.png")
        if args.tile_sheets:
            for i in own_tile_palettes(tileset):
                render_tile_sheet(tileset, palettes[i]).save(out_dir / f"tiles_pal{i:02}.png")

        paired = f" (with {primary.name})" if primary else ""
        print(f"  {tileset.name}{paired}")

    print(f"Done. Images written to {args.out}")


if __name__ == "__main__":
    main()
