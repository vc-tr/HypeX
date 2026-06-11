"""Fetch the manhwa/webtoon title universe from the AniList GraphQL API.

Universe rules (set with the project owner):
  - Medium scope : Korean-origin comics (countryOfOrigin == "KR") = manhwa / webtoons
  - Size         : top ~100 titles
  - Ranking      : BALANCED blend of all-time hype (popularity, magnitude-preserving)
                   and current hype (trending). WEIGHT_ALLTIME = 0.75.
  - Cohorts      : genre + debut-year (decade). Webtoon-vs-print kept as a bonus flag
                   derived from the AniList "Long Strip" tag.

Outputs:
  candidates.csv  raw ranked universe with metrics, scores, genres (provenance)
  titles.csv      clean registry used by the analytics pipeline

Stdlib only (urllib) so it runs anywhere with no extra deps.
"""

from __future__ import annotations

import csv
import json
import math
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://graphql.anilist.co"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ── Universe knobs ───────────────────────────────────────────────────────
TARGET_SIZE = 100          # final number of titles to keep
WEIGHT_ALLTIME = 0.75      # weight on all-time hype; current hype gets (1 - this)
POP_PAGES = 5              # pages of POPULARITY_DESC to pull (50/page)
TREND_PAGES = 2            # pages of TRENDING_DESC to pull (50/page)
LONGSTRIP_MIN_RANK = 40    # AniList "Long Strip" tag rank >= this => format "webtoon"

# Tags that describe format/cast rather than story theme — excluded when picking
# the headline `theme` cohort (AniList genres are ~84% "Action" so are too coarse).
FORMAT_CAST_TAGS = {
    "Long Strip", "Full Color", "Male Protagonist", "Female Protagonist",
    "Primarily Male Cast", "Primarily Female Cast", "Primarily Adult Cast",
    "Ensemble Cast", "Adult Cast", "Heterosexual", "Anti-Hero", "Primarily Teen Cast",
}

QUERY = """
query ($page: Int, $sort: [MediaSort]) {
  Page(page: $page, perPage: 50) {
    pageInfo { currentPage hasNextPage }
    media(type: MANGA, countryOfOrigin: KR, sort: $sort, isAdult: false) {
      id
      title { romaji english native }
      synonyms
      format
      status
      startDate { year }
      popularity
      favourites
      trending
      genres
      tags { name rank }
      siteUrl
    }
  }
}
"""


def _post(variables: dict, retries: int = 4) -> dict:
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA},
    )
    for _ in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", "5"))
                print(f"    rate-limited, waiting {wait}s...")
                time.sleep(wait + 1)
                continue
            raise
    raise RuntimeError("AniList request failed after retries")


def fetch_sorted(sort: str, pages: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for page in range(1, pages + 1):
        block = _post({"page": page, "sort": [sort]})["data"]["Page"]
        for m in block["media"]:
            out[m["id"]] = m
        print(f"  [{sort}] page {page}: +{len(block['media'])} (total {len(out)})")
        if not block["pageInfo"]["hasNextPage"]:
            break
        time.sleep(0.7)
    return out


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "title"


def log_minmax(values: list[float]) -> dict[float, float]:
    """Magnitude-preserving normalization to [0,1] on a log scale."""
    logs = {v: math.log1p(max(0.0, v)) for v in set(values)}
    lo, hi = min(logs.values()), max(logs.values())
    span = (hi - lo) or 1.0
    return {v: (lg - lo) / span for v, lg in logs.items()}


def minmax(values: list[float]) -> dict[float, float]:
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    return {v: (v - lo) / span for v in set(values)}


def main() -> None:
    print("Fetching all-time-hype titles (POPULARITY_DESC)...")
    pop = fetch_sorted("POPULARITY_DESC", POP_PAGES)
    print("Fetching current-hype titles (TRENDING_DESC)...")
    trend = fetch_sorted("TRENDING_DESC", TREND_PAGES)

    media = list({**trend, **pop}.values())  # union by id
    print(f"\nUnion universe: {len(media)} unique KR titles")

    # BALANCED blend: log-magnitude popularity (all-time) + linear trending (current)
    pop_norm = log_minmax([m.get("popularity") or 0 for m in media])
    trend_norm = minmax([m.get("trending") or 0 for m in media])
    for m in media:
        a = pop_norm[m.get("popularity") or 0]
        c = trend_norm[m.get("trending") or 0]
        m["_score"] = WEIGHT_ALLTIME * a + (1 - WEIGHT_ALLTIME) * c

    media.sort(key=lambda m: m["_score"], reverse=True)
    top = media[:TARGET_SIZE]

    rows, seen = [], {}
    for rank, m in enumerate(top, 1):
        t = m["title"]
        name = t.get("english") or t.get("romaji") or t.get("native") or f"title-{m['id']}"
        slug = slugify(t.get("english") or t.get("romaji") or name)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"

        is_webtoon = any(
            tag["name"] == "Long Strip" and (tag.get("rank") or 0) >= LONGSTRIP_MIN_RANK
            for tag in (m.get("tags") or [])
        )
        genres = m.get("genres") or []
        # headline story theme = highest-ranked tag that isn't a format/cast descriptor
        theme = next(
            (tag["name"] for tag in sorted(m.get("tags") or [], key=lambda x: -(x.get("rank") or 0))
             if tag["name"] not in FORMAT_CAST_TAGS and (tag.get("rank") or 0) > 0),
            genres[0] if genres else "Unknown",
        )
        year = (m.get("startDate") or {}).get("year")
        variants = [t.get("romaji"), t.get("english"), t.get("native"), *(m.get("synonyms") or [])]
        aliases = sorted({v.strip() for v in variants if v and v.strip() and v.strip() != name})

        rows.append({
            "rank": rank,
            "canonical_id": slug,
            "canonical_name": name,
            "medium": "webtoon" if is_webtoon else "manhwa",
            "language": "ko",
            "year": year or "",
            "decade": f"{(year // 10) * 10}s" if year else "",
            "primary_genre": genres[0] if genres else "Unknown",
            "theme": theme,
            "genres": "|".join(genres),
            "popularity": m.get("popularity") or 0,
            "favourites": m.get("favourites") or 0,
            "trending": m.get("trending") or 0,
            "blended_score": round(m["_score"], 4),
            "native": t.get("native") or "",
            "aliases": "|".join(aliases),
            "site_url": m.get("siteUrl") or "",
            "anilist_id": m["id"],
        })

    out_dir = Path(__file__).resolve().parent
    # full provenance file
    with (out_dir / "candidates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # clean registry for the analytics pipeline
    reg_cols = ["canonical_id", "canonical_name", "medium", "language", "year",
                "decade", "primary_genre", "theme", "genres", "aliases", "anilist_id"]
    with (out_dir / "titles.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=reg_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # ── summary ──
    n_web = sum(r["medium"] == "webtoon" for r in rows)
    from collections import Counter
    themes = Counter(r["theme"] for r in rows)
    decades = Counter(r["decade"] for r in rows)
    print(f"\nWrote {len(rows)} titles -> candidates.csv + titles.csv")
    print(f"  format flag : webtoon {n_web} / manhwa(print) {len(rows) - n_web}")
    print(f"  theme cohort : {dict(themes.most_common(12))}")
    print(f"  decade       : {dict(sorted(decades.items()))}")
    print(f"\nTop 25 (BALANCED {WEIGHT_ALLTIME:.0%} all-time / {1-WEIGHT_ALLTIME:.0%} current):")
    print(f"{'#':>3}  {'name':<33} {'genre':<12} {'yr':<5} {'pop':>7} {'trend':>5}")
    for r in rows[:25]:
        print(f"{r['rank']:>3}  {r['canonical_name'][:32]:<33} {r['primary_genre'][:11]:<12} "
              f"{str(r['year']):<5} {r['popularity']:>7} {r['trending']:>5}")


if __name__ == "__main__":
    main()
