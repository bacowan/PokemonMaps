"""Convert a raster map (GeoTIFF) into a Pokemon-style map.

Usage:
  py scripts/raster_to_pokemon.py <input.tif> <output path>
"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tif", type=Path, help="input .tif raster")
    parser.add_argument("out", type=Path, help="where to write the output")
    args = parser.parse_args()

    if not args.tif.is_file():
        parser.error(f"input file not found: {args.tif}")

    # TODO: load the raster, convert it, and write the result to args.out
    print(f"input: {args.tif}")
    print(f"output: {args.out}")


if __name__ == "__main__":
    main()
