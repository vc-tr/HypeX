import type { SourcePlugin, SourceTitle } from "@hypex/core";

/** Example source plugin - replace with real ingestion logic */
const plugin: SourcePlugin = {
  id: "example",
  name: "Example Source",

  async fetchTitles(): Promise<SourceTitle[]> {
    return [
      { externalId: "ex-1", name: "Solo Leveling", type: "manhwa" },
      { externalId: "ex-2", name: "One Piece", type: "manga" },
    ];
  },
};

export default plugin;
