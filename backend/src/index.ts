import express from "express";

const app = express();
const port = Number(process.env.PORT ?? 3001);

app.get("/api/hello", (_req, res) => {
  res.json({ message: "Hello from Express!" });
});

app.listen(port, () => {
  console.log(`Backend listening on http://localhost:${port}`);
});
