"""Price the real Track-2 signal from stored Google Trends interest.

Reads metrics_real.csv (daily, forward-filled interest), reprices each title at
its native WEEKLY cadence (see pricing.price_real_series), then forward-fills the
resulting prices back to daily so the real track aligns with the synthetic one.
Runs offline — no Trends API calls.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from pricing import price_real_series

EXPORTS = Path(__file__).resolve().parents[1] / "data" / "exports"
END_DATE = date(2026, 6, 11)
DAYS = 730
START_DATE = END_DATE - timedelta(days=DAYS - 1)


def _ffill_daily(weekly_series: pd.Series, daily_index: pd.DatetimeIndex) -> pd.Series:
    return (weekly_series.reindex(weekly_series.index.union(daily_index))
            .ffill().reindex(daily_index).ffill().bfill())


def main() -> None:
    m = pd.read_csv(EXPORTS / "metrics_real.csv", parse_dates=["date"])
    daily_index = pd.date_range(START_DATE, END_DATE, freq="D")
    out_rows = []

    for cid, g in m.groupby("canonical_id"):
        weekly = g.sort_values("date").set_index("date")["search_interest"].resample("W").mean()
        hs_w, px_w = price_real_series(weekly.tolist())
        hs_daily = _ffill_daily(pd.Series(hs_w, index=weekly.index), daily_index)
        px_daily = _ffill_daily(pd.Series(px_w, index=weekly.index), daily_index)
        for d in daily_index:
            out_rows.append((d.date().isoformat(), cid,
                             round(float(hs_daily[d]), 4), round(float(px_daily[d]), 2), "real"))

    with (EXPORTS / "prices_real.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "canonical_id", "hype_index", "price", "track"])
        w.writerows(out_rows)

    finals = {cid: px for (_, cid, _, px, _) in out_rows}  # last date wins
    vals = list(finals.values())
    print(f"Repriced {len(finals)} real titles -> prices_real.csv ({len(out_rows):,} rows)")
    print(f"  final price range: {min(vals):.1f} .. {max(vals):.1f}  "
          f"({sum(v > 100 for v in vals)} up / {sum(v < 100 for v in vals)} down)")


if __name__ == "__main__":
    main()
