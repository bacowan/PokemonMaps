import express from "express";
import { readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = express();
const port = Number(process.env.PORT ?? 3001);

const tilesetsDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../scripts/output/tilesets",
);
const metatilesDir = path.join(tilesetsDir, "primary/general/metatiles");

app.use("/api/tilesets", express.static(tilesetsDir));

app.get("/api/hello", (_req, res) => {
  res.json({ message: "Hello from Express!" });
});

app.get("/api/map", (req, res) => {
  const width = Number(req.query.width ?? 100);
  const height = Number(req.query.height ?? 100);
  const metatiles = readdirSync(metatilesDir)
    .filter((f) => f.endsWith(".png"))
    .map((f) => `primary/general/metatiles/${f}`);

  const tiles = Array.from(
    { length: width * height },
    () => metatiles[Math.floor(Math.random() * metatiles.length)],
  );
  res.json({ width, height, tileSize: 16, tiles });
});

app.listen(port, () => {
  console.log(`Backend listening on http://localhost:${port}`);
});
