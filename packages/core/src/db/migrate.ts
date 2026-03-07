#!/usr/bin/env node
import { getDb } from "./client.js";

getDb();
console.log("Database initialized at:", process.env.DATABASE_PATH ?? "./data/hypex.db");
console.log("Schema applied.");
