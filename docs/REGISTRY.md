# HypeX Registry

The canonical title registry lives in `data/registry/`. It is the source of truth for titles and aliases, synced into Postgres by the worker.

## CSV Schema: `titles.csv`

| Column         | Required | Description                                      |
|----------------|----------|--------------------------------------------------|
| canonical_id   | No       | Slug (kebab-case). If empty, generated from `canonical_name`. |
| canonical_name | Yes      | Display name of the title                        |
| medium         | Yes      | `manga` \| `manhwa` \| `manhua` \| `webtoon`     |
| language       | Yes      | e.g. `ja`, `ko`, `en`                            |
| aliases        | No       | Pipe-separated list: `OP\|ワンピース\|One Piece` |
| platform       | No       | Optional platform                                |
| year           | No       | Optional year (integer)                          |

### Example

```csv
canonical_id,canonical_name,medium,language,aliases,platform,year
one-piece,One Piece,manga,ja,OP|ワンピース,,1997
naruto,Naruto,manga,ja,,,1999
```

## Aliases: `aliases.json`

Maps alias strings to `canonical_id`. Format: `{ "alias": "canonical_id", ... }`.

### Example

```json
{
  "OP": "one-piece",
  "ワンピース": "one-piece",
  "JJK": "jujutsu-kaisen"
}
```

## Syncing

Run:

```bash
python -m apps.worker.sync_titles
```

### How it works

1. **Load** — Reads `data/registry/titles.csv` and `data/registry/aliases.json`.
2. **Canonical ID** — Uses `canonical_id` from CSV if present; otherwise generates a kebab-case slug from `canonical_name`.
3. **Merge aliases** — Combines aliases from:
   - CSV `aliases` column (pipe-separated)
   - `aliases.json` entries for that `canonical_id`
   - Deduplicates (case-insensitive) and sorts.
4. **Upsert** — Inserts or updates rows in Postgres `titles` table.
5. **Idempotent** — On conflict, merges new aliases with existing DB aliases (no duplicates). Sets `updated_at = now()` on changes.

### Postgres columns

Synced fields: `canonical_id`, `canonical_name`, `medium`, `language`, `aliases` (JSONB array), `platform`, `year`. The sync also sets `updated_at` on every update.
