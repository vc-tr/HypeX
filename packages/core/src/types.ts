/** Canonical title in the registry */
export interface Title {
  id: string;
  canonicalName: string;
  type: "manga" | "manhwa" | "manhua" | "webtoon";
  aliases: string[];
  createdAt: string;
}

/** Alias mapping for resolution */
export interface AliasEntry {
  alias: string;
  titleId: string;
}

/** Daily hype index + price series */
export interface PricePoint {
  titleId: string;
  date: string; // YYYY-MM-DD
  hypeIndex: number;
  price?: number; // for paper trading
}

/** Catalyst / event on the timeline */
export interface Event {
  id: string;
  titleId: string;
  type: "release" | "announcement" | "milestone" | "adaptation" | "other";
  label: string;
  date: string;
  metadata?: Record<string, unknown>;
}

/** Source plugin contract */
export interface SourcePlugin {
  id: string;
  name: string;
  fetchTitles(): Promise<SourceTitle[]>;
  fetchHype?(titleIds: string[]): Promise<SourceHype[]>;
}

export interface SourceTitle {
  externalId: string;
  name: string;
  type: Title["type"];
  aliases?: string[];
}

export interface SourceHype {
  externalId: string;
  hypeIndex: number;
  date?: string;
}
