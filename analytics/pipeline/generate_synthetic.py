"""Track 1 — synthetic daily demand signal + prices for the full 100-title universe.

The synthetic signal is deterministic (seeded per title) and internally consistent
with each title's REAL AniList stats:
  - baseline mention volume scales with real `popularity`
  - a 2-year drift is driven by real `trending` (hot titles rise, stale ones fade)
  - weekly "chapter release" spikes + multiplicative noise + rare news spikes

Prices come from the shared, documented model in pricing.py (same one Track 2 uses),
so synthetic and real series are directly comparable.

Outputs (the star schema the dashboard/notebooks consume):
  analytics/data/exports/metrics.csv   date, canonical_id, mentions_count, engagement_score, track
  analytics/data/exports/prices.csv    date, canonical_id, hype_index, price, track
  analytics/data/exports/titles.csv    dimension table (cohorts + real stats)
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

from pricing import compute_hype_index, compute_prices, rolling_zscore, smooth_hype

# ── Config ───────────────────────────────────────────────────────────────
END_DATE = date(2026, 6, 11)   # hard-coded for reproducible reruns
DAYS = 730                      # ~2 years of daily history
TREND_REF = 67.0               # max trending in the universe (normalizer)
IDIO_SIGMA = 0.020             # idiosyncratic daily-return noise: real prices are
#                                mostly unpredictable; hype is a small drift on top

HERE = Path(__file__).resolve().parents[1]          # analytics/
UNIVERSE = HERE / "universe" / "candidates.csv"
OUT = HERE / "data" / "exports"


def daterange() -> list[date]:
    start = END_DATE - timedelta(days=DAYS - 1)
    return [start + timedelta(days=i) for i in range(DAYS)]


def synth_metrics(row: dict, dates: list[date]) -> tuple[list[float], list[float]]:
    """Return (mentions_count, engagement_score) daily series for one title."""
    pop = float(row["popularity"] or 0)
    trend = float(row["trending"] or 0)
    rng = random.Random(hash(row["canonical_id"]) & 0xFFFFFFFF)

    base = 10.0 + pop / 3000.0                       # baseline daily mentions
    eng_ratio = rng.uniform(0.4, 1.4)                # per-title engagement intensity
    release_dow = rng.randint(0, 6)                  # weekly "chapter drop" weekday
    phase = rng.uniform(0, 2 * math.pi)              # annual-season phase

    # 2-year drift from real current-hype: hot titles climb, stale ones drift down
    tr = min(trend / TREND_REF, 1.0)
    # neutral near the universe's typical trending so the market centers ~100:
    # genuinely-hot titles climb, faded classics drift down only mildly
    g_annual = max(-0.25, min(0.80, (tr - 0.15) * 0.8))
    end_factor = (1.0 + g_annual) ** 1.5             # total multiplier over the window

    mentions, engagement = [], []
    spike_left, spike_mult = 0, 1.0
    for i, d in enumerate(dates):
        long_trend = math.exp(math.log(end_factor) * (i / DAYS))
        season = 1.0 + 0.10 * math.sin(2 * math.pi * i / 365.0 + phase)
        weekly = 1.9 if d.weekday() == release_dow else (1.1 if d.weekday() >= 5 else 1.0)
        noise = math.exp(rng.gauss(0, 0.18))

        if spike_left == 0 and rng.random() < 0.012:  # rare news/season spike
            spike_left = rng.randint(1, 4)
            spike_mult = rng.uniform(1.8, 3.5)
        spike = spike_mult if spike_left > 0 else 1.0
        if spike_left > 0:
            spike_left -= 1

        m = max(0.0, base * long_trend * season * weekly * noise * spike)
        e = max(0.0, m * eng_ratio * math.exp(rng.gauss(0, 0.22)))
        mentions.append(round(m, 1))
        engagement.append(round(e, 1))
    return mentions, engagement


def main() -> None:
    titles = list(csv.DictReader(UNIVERSE.open(encoding="utf-8")))
    dates = daterange()
    iso = [d.isoformat() for d in dates]
    OUT.mkdir(parents=True, exist_ok=True)

    m_rows, p_rows = [], []
    for row in titles:
        mentions, engagement = synth_metrics(row, dates)
        z_m = rolling_zscore(mentions)
        z_e = rolling_zscore(engagement)
        hs = smooth_hype(compute_hype_index(z_m, z_e))
        prices = compute_prices(hs)
        # idiosyncratic random-walk overlay so returns are realistically noisy
        irng = random.Random((hash(row["canonical_id"]) & 0xFFFFFFFF) ^ 0x5BD1E995)
        acc = 0.0
        adj = []
        for p in prices:
            acc += irng.gauss(0, IDIO_SIGMA) - 0.5 * IDIO_SIGMA ** 2  # de-meaned: return-neutral
            adj.append(p * math.exp(acc))
        prices = adj
        cid = row["canonical_id"]
        for k in range(len(dates)):
            m_rows.append((iso[k], cid, mentions[k], engagement[k], "synthetic"))
            p_rows.append((iso[k], cid, round(hs[k], 4), round(prices[k], 2), "synthetic"))

    with (OUT / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "canonical_id", "mentions_count", "engagement_score", "track"])
        w.writerows(m_rows)
    with (OUT / "prices.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "canonical_id", "hype_index", "price", "track"])
        w.writerows(p_rows)

    # dimension table
    dim_cols = ["canonical_id", "canonical_name", "medium", "language", "year",
                "decade", "primary_genre", "theme", "popularity", "favourites",
                "trending", "anilist_id"]
    with (OUT / "titles.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dim_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(titles)

    # sanity summary
    finals = {}
    for iso_d, cid, hs_v, price, _ in p_rows:
        finals[cid] = price  # last write wins == last date
    top = sorted(finals.items(), key=lambda kv: kv[1], reverse=True)[:8]
    name = {t["canonical_id"]: t["canonical_name"] for t in titles}
    print(f"Wrote {len(m_rows):,} metric rows + {len(p_rows):,} price rows")
    print(f"  titles: {len(titles)}   dates: {iso[0]} .. {iso[-1]} ({DAYS} days)")
    print(f"  price range: {min(finals.values()):.1f} .. {max(finals.values()):.1f}  (P0=100)")
    print("  highest final price (most sustained hype growth):")
    for cid, pr in top:
        print(f"    {pr:7.1f}  {name[cid]}")


if __name__ == "__main__":
    main()
