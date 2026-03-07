import { describe, it, expect } from "vitest";
import {
  resolveAlias,
  mergeAliases,
  normalizeTitle,
  titlesMatch,
} from "./registry.js";

describe("resolveAlias", () => {
  const aliases = [
    { alias: "solo leveling", titleId: "t1" },
    { alias: "one piece", titleId: "t2" },
  ];

  it("resolves exact match", () => {
    expect(resolveAlias(aliases, "Solo Leveling")).toBe("t1");
  });

  it("returns null for unknown alias", () => {
    expect(resolveAlias(aliases, "Unknown Title")).toBeNull();
  });
});

describe("mergeAliases", () => {
  it("deduplicates and merges", () => {
    expect(mergeAliases(["a", "B"], ["b", "c"])).toEqual(
      expect.arrayContaining(["a", "b", "c"])
    );
  });
});

describe("normalizeTitle", () => {
  it("lowercases and trims", () => {
    expect(normalizeTitle("  Solo  Leveling  ")).toBe("solo leveling");
  });
});

describe("titlesMatch", () => {
  it("matches when normalized", () => {
    expect(titlesMatch("Solo Leveling", "solo leveling")).toBe(true);
  });
  it("does not match different titles", () => {
    expect(titlesMatch("Solo Leveling", "One Piece")).toBe(false);
  });
});
