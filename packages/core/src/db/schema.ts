export const SCHEMA = `
-- Canonical titles
CREATE TABLE IF NOT EXISTS titles (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('manga', 'manhwa', 'manhua', 'webtoon')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Aliases for resolution
CREATE TABLE IF NOT EXISTS aliases (
  alias TEXT NOT NULL,
  title_id TEXT NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
  PRIMARY KEY (alias, title_id)
);
CREATE INDEX IF NOT EXISTS idx_aliases_title_id ON aliases(title_id);

-- Daily hype index + price series
CREATE TABLE IF NOT EXISTS price_points (
  title_id TEXT NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  hype_index REAL NOT NULL,
  price REAL,
  PRIMARY KEY (title_id, date)
);
CREATE INDEX IF NOT EXISTS idx_price_points_date ON price_points(date);

-- Catalyst events
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title_id TEXT NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  label TEXT NOT NULL,
  date TEXT NOT NULL,
  metadata TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_title_id ON events(title_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
`;
