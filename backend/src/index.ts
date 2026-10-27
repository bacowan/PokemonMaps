import express from "express";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = express();
const port = Number(process.env.PORT ?? 3001);
const isProd = process.env.NODE_ENV === "production";

const TILE_SIZE = 16;

const scriptsDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../scripts",
);
const renderDir = path.join(scriptsDir, "output/render");

interface RenderMeta {
  width: number;
  height: number;
  tiles: Record<string, number>;
}

// render.bin holds the same grid as render.tif (one uint8 per tile, row-major),
// without needing a TIFF decoder.
const render: RenderMeta = JSON.parse(
  readFileSync(path.join(renderDir, "render.json"), "utf8"),
);
const grid = readFileSync(path.join(renderDir, "render.bin"));
if (grid.length !== render.width * render.height) {
  throw new Error(
    `render.bin has ${grid.length} tiles, expected ${render.width}x${render.height}`,
  );
}

// render.cells.json holds per-cell metadata as one [row][col] grid per field.
const cells: Record<string, unknown[][]> = JSON.parse(
  readFileSync(path.join(renderDir, "render.cells.json"), "utf8"),
);
for (const [field, rows] of Object.entries(cells)) {
  if (rows.length !== render.height || rows.some((row) => row.length !== render.width)) {
    throw new Error(
      `render.cells.json field "${field}" is not ${render.width}x${render.height}`,
    );
  }
}

// Clamps the x/y/width/height query parameters to the map.
function queryRegion(query: Record<string, unknown>) {
  const x0 = Math.max(0, Math.floor(Number(query.x ?? 0)));
  const y0 = Math.max(0, Math.floor(Number(query.y ?? 0)));
  const x1 = Math.min(render.width, x0 + Math.floor(Number(query.width ?? 0)));
  const y1 = Math.min(render.height, y0 + Math.floor(Number(query.height ?? 0)));
  return { x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0) };
}

// tiles.json image paths are relative to scripts/, e.g. "output/tilesets/...".
app.use(
  "/api/output",
  express.static(path.join(scriptsDir, "output"), { maxAge: isProd ? "1d" : 0 }),
);

app.get("/api/tiles.json", (_req, res) => {
  res.sendFile(path.join(scriptsDir, "config", "tiles.json"));
});

app.get("/api/hello", (_req, res) => {
  res.json({ message: "Hello from Express!" });
});

app.get("/api/map", (_req, res) => {
  res.json({
    width: render.width,
    height: render.height,
    tileSize: TILE_SIZE,
    tiles: render.tiles,
  });
});

app.get("/api/map/tiles", (req, res) => {
  const region = queryRegion(req.query);
  const tiles: number[] = [];
  for (let y = region.y; y < region.y + region.height; y++) {
    const row = y * render.width;
    for (let x = region.x; x < region.x + region.width; x++) tiles.push(grid[row + x]);
  }
  res.json({ ...region, tiles });
});

// Each metadata field is flattened row-major over the region, like tiles.
app.get("/api/map/meta", (req, res) => {
  const region = queryRegion(req.query);
  const fields: Record<string, unknown[]> = {};
  for (const [field, rows] of Object.entries(cells)) {
    const values: unknown[] = [];
    for (let y = region.y; y < region.y + region.height; y++) {
      values.push(...rows[y].slice(region.x, region.x + region.width));
    }
    fields[field] = values;
  }
  res.json({ ...region, fields });
});

app.listen(port, () => {
  console.log(`Backend listening on http://localhost:${port}`);
});
