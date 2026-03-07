#!/usr/bin/env node
import { getDb } from "./client.js";

const db = getDb();

// Example seed: a few placeholder titles
const titles = [
  { id: "ex-1", canonicalName: "Solo Leveling", type: "manhwa" },
  { id: "ex-2", canonicalName: "One Piece", type: "manga" },
  { id: "ex-3", canonicalName: "Tower of God", type: "webtoon" },
];

for (const t of titles) {
  db.prepare(
    "INSERT OR IGNORE INTO titles (id, canonical_name, type) VALUES (?, ?, ?)"
  ).run(t.id, t.canonicalName, t.type);
}

console.log(`Seeded ${titles.length} titles.`);
