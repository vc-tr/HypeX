"""Track 2 — pull the REAL demand signal (Google Trends weekly search interest)
for the curated top-N titles and store it raw. Pricing happens separately in
analytics/pipeline/reprice_real.py (at weekly resolution).

Google Trends returns WEEKLY, RELATIVE (0-100) interest; we forward-fill to daily
to align with the synthetic track's daily metrics.

Usage:
  python fetch_trends.py [--limit N] [--sleep SECONDS] [--resume]
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from pytrends.request import TrendReq

HERE = Path(__file__).resolve().parents[1]                 # analytics/
END_DATE = date(2026, 6, 11)
DAYS = 730
START_DATE = END_DATE - timedelta(days=DAYS - 1)
TIMEFRAME = f"{START_DATE.isoformat()} {END_DATE.isoformat()}"
QUERY_MAP = Path(__file__).resolve().parent / "query_map.csv"
OUT = HERE / "data" / "exports"


def fetch_one(pt: TrendReq, query: str, retries: int = 5):
    """Return a weekly interest Series for `query`, or None."""
    for attempt in range(retries):
        try:
            pt.build_payload([query], timeframe=TIMEFRAME, geo="")
            df = pt.interest_over_time()
            if df.empty:
                return None
            return df[query]
        except Exception as e:  # 429 / parsing / network
            wait = 12 * (attempt + 1)
            print(f"    retry {attempt+1}/{retries} ({type(e).__name__}); waiting {wait}s")
            time.sleep(wait)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only first N titles (0 = all)")
    ap.add_argument("--sleep", type=float, default=3.0, help="seconds between titles")
    ap.add_argument("--resume", action="store_true", help="skip titles already fetched, append")
    args = ap.parse_args()

    rows = list(csv.DictReader(QUERY_MAP.open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]

    OUT.mkdir(parents=True, exist_ok=True)
    metrics_path = OUT / "metrics_real.csv"
    resume = args.resume and metrics_path.exists()
    if resume:
        done = set(pd.read_csv(metrics_path, usecols=["canonical_id"])["canonical_id"].unique())
        rows = [r for r in rows if r["canonical_id"] not in done]
        print(f"Resume: {len(done)} already fetched, {len(rows)} remaining")

    daily_index = pd.date_range(START_DATE, END_DATE, freq="D")
    pt = TrendReq(hl="en-US", tz=0)
    ok, miss = [], []

    mfile = metrics_path.open("a" if resume else "w", newline="", encoding="utf-8")
    mw = csv.writer(mfile)
    if not resume:
        mw.writerow(["date", "canonical_id", "search_interest", "track"])

    for r in rows:
        cid, query = r["canonical_id"], r["query"]
        print(f"[{r['rank']}] {query!r} ...", end=" ", flush=True)
        s = fetch_one(pt, query)
        if s is None:
            print("NO DATA")
            miss.append(query)
            time.sleep(args.sleep)
            continue

        daily = s.reindex(s.index.union(daily_index)).interpolate().reindex(daily_index).ffill().bfill()
        for k, d in enumerate(daily_index):
            mw.writerow((d.date().isoformat(), cid, round(float(daily.iloc[k]), 2), "real"))
        mfile.flush()
        print(f"ok (weekly pts: {len(s)}, peak {s.max():.0f})")
        ok.append(query)
        time.sleep(args.sleep)

    mfile.close()
    print(f"\nDone. ok={len(ok)} miss={len(miss)}  -> metrics_real.csv  (run reprice_real.py to price)")
    if miss:
        print("  no data for:", miss)


if __name__ == "__main__":
    main()
