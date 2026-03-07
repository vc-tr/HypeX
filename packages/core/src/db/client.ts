import Database from "better-sqlite3";
import { mkdirSync, existsSync } from "fs";
import { dirname } from "path";
import { SCHEMA } from "./schema.js";

const DB_PATH = process.env.DATABASE_PATH ?? "./data/hypex.db";

function ensureDbDir(): void {
  const dir = dirname(DB_PATH);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

let db: ReturnType<typeof Database> | null = null;

export function getDb(): ReturnType<typeof Database> {
  if (!db) {
    ensureDbDir();
    db = new Database(DB_PATH);
    db.exec(SCHEMA);
  }
  return db;
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}
