import type { AliasEntry } from "./types.js";

/** Resolve alias to canonical title ID */
export function resolveAlias(aliases: AliasEntry[], query: string): string | null {
  const normalized = query.toLowerCase().trim();
  const entry = aliases.find(
    (a) => a.alias.toLowerCase() === normalized
  );
  return entry?.titleId ?? null;
}

/** Merge aliases from multiple sources, deduplicated */
export function mergeAliases(existing: string[], incoming: string[]): string[] {
  const set = new Set(existing.map((a) => a.toLowerCase()));
  for (const a of incoming) {
    const lower = a.toLowerCase().trim();
    if (lower) set.add(lower);
  }
  return [...set];
}

/** Normalize title for matching */
export function normalizeTitle(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/** Check if two titles likely refer to the same work */
export function titlesMatch(a: string, b: string): boolean {
  return normalizeTitle(a) === normalizeTitle(b);
}
