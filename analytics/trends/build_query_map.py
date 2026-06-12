"""Build the curated Google Trends query map for the top-N titles (Track 2).

Google Trends matches raw search strings, so ambiguous titles ("Bastard",
"Sweet Home", "Pick Me Up") need a disambiguating qualifier or they pull
unrelated search volume. Curation below was reviewed with the project owner.
"""

from __future__ import annotations

import csv
from pathlib import Path

TOP_N = 30
QUALIFIER = "webtoon"
HERE = Path(__file__).resolve().parents[1]            # analytics/
CANDIDATES = HERE / "universe" / "candidates.csv"
OUT = Path(__file__).resolve().parent / "query_map.csv"

# Generic-English titles that need a disambiguating qualifier
NEEDS_QUALIFIER = {
    "Nano Machine", "Pick Me Up", "Bastard", "The Horizon",
    "Teenage Mercenary", "Sweet Home", "The Boxer",
}
# Exact-query overrides (fuller / cleaner official search terms)
OVERRIDES = {
    "Omniscient Reader": "Omniscient Reader's Viewpoint",
    "66,666 Years: Advent of the Dark Mage": "Advent of the Dark Mage",
}
# Titles whose real Trends signal is known to be contaminated (kept, but flagged)
NOISY = {"Sweet Home"}  # large Netflix adaptation inflates/distorts search volume


def normalize(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'")


def propose(name: str) -> tuple[str, str]:
    name = normalize(name)
    if name in OVERRIDES:
        return OVERRIDES[name], "override"
    if name in NEEDS_QUALIFIER:
        return f"{name} {QUALIFIER}", "qualified"
    return name, ""


def main() -> None:
    rows = list(csv.DictReader(CANDIDATES.open(encoding="utf-8")))[:TOP_N]
    out_rows = []
    for r in rows:
        name = normalize(r["canonical_name"])
        query, status = propose(r["canonical_name"])
        out_rows.append({
            "rank": r["rank"],
            "canonical_id": r["canonical_id"],
            "canonical_name": name,
            "query": query,
            "status": status,
            "noisy": "yes" if name in NOISY else "",
        })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "canonical_id", "canonical_name", "query", "status", "noisy"])
        w.writeheader()
        w.writerows(out_rows)

    n_custom = sum(1 for r in out_rows if r["status"])
    print(f"Wrote {OUT}  ({len(out_rows)} titles, {n_custom} customized)\n")
    print(f"{'#':>3}  {'title':<38} {'Trends query':<34} {'status'}")
    print("-" * 92)
    for r in out_rows:
        tag = r["status"] + ("/noisy" if r["noisy"] else "")
        print(f"{r['rank']:>3}  {r['canonical_name'][:37]:<38} {r['query'][:33]:<34} {tag}")


if __name__ == "__main__":
    main()
