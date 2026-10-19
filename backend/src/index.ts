import express from "express";
import { readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = express();
const port = Number(process.env.PORT ?? 3001);
const isProd = process.env.NODE_ENV === "production";

const MAP_WIDTH = 100;
const MAP_HEIGHT = 100;
const TILE_SIZE = 16;

const tilesetsDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../scripts/output/tilesets",
);
const metatilesDir = path.join(tilesetsDir, "primary/general/metatiles");
const metatiles = readdirSync(metatilesDir)
  .filter((f) => f.endsWith(".png"))
  .map((f) => path.basename(f, ".png"))
  .sort();

app.use(
  "/api/tilesets",
  express.static(tilesetsDir, { maxAge: isProd ? "1d" : 0 }),
);

app.get("/api/hello", (_req, res) => {
  res.json({ message: "Hello from Express!" });
});

// Stable pseudo-random tile per coordinate, so overlapping region requests agree.
function tileAt(x: number, y: number): string {
  let h = Math.imul(x, 0x27d4eb2d) ^ Math.imul(y, 0x165667b1);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h ^= h >>> 13;
  return metatiles[(h >>> 0) % metatiles.length];
}

app.get("/api/map", (_req, res) => {
  res.json({ width: MAP_WIDTH, height: MAP_HEIGHT, tileSize: TILE_SIZE });
});

app.get("/api/map/tiles", (req, res) => {
  const x0 = Math.max(0, Math.floor(Number(req.query.x ?? 0)));
  const y0 = Math.max(0, Math.floor(Number(req.query.y ?? 0)));
  const x1 = Math.min(MAP_WIDTH, x0 + Math.floor(Number(req.query.width ?? 0)));
  const y1 = Math.min(MAP_HEIGHT, y0 + Math.floor(Number(req.query.height ?? 0)));
  const width = Math.max(0, x1 - x0);
  const height = Math.max(0, y1 - y0);

  const tiles: string[] = [];
  for (let y = y0; y < y0 + height; y++) {
    for (let x = x0; x < x0 + width; x++) tiles.push(tileAt(x, y));
  }
  res.json({ x: x0, y: y0, width, height, tiles });
});

app.listen(port, () => {
  console.log(`Backend listening on http://localhost:${port}`);
});
