"""Combine Track 1 (synthetic, 100 titles) and Track 2 (real Trends, ~30) into
dashboard-ready exports.

  prices_all.csv    synthetic (all 100) + real (the 30) stacked, distinguished by
                    `track` — so the dashboard can overlay synthetic vs real.
  titles_dim.csv    dimension table + `has_real_data` flag.
  market_index.csv  daily equal-weight average price per track (the "HypeX Index").
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPORTS = Path(__file__).resolve().parents[1] / "data" / "exports"


def main() -> None:
    syn = pd.read_csv(EXPORTS / "prices.csv", parse_dates=["date"])
    titles = pd.read_csv(EXPORTS / "titles.csv")

    real_path = EXPORTS / "prices_real.csv"
    if real_path.exists():
        real = pd.read_csv(real_path, parse_dates=["date"])
    else:
        real = syn.iloc[0:0]
    real_ids = set(real["canonical_id"].unique())

    prices_all = pd.concat([syn, real], ignore_index=True)
    prices_all.to_csv(EXPORTS / "prices_all.csv", index=False)

    titles["has_real_data"] = titles["canonical_id"].isin(real_ids)
    titles.to_csv(EXPORTS / "titles_dim.csv", index=False)

    # daily equal-weight "HypeX Index" per track
    idx = (prices_all.groupby(["date", "track"])["price"].mean()
           .reset_index().rename(columns={"price": "index_level"}))
    idx.to_csv(EXPORTS / "market_index.csv", index=False)

    print(f"prices_all : {len(prices_all):,} rows ({syn['canonical_id'].nunique()} synthetic, "
          f"{len(real_ids)} real)")
    print(f"titles_dim : {len(titles)} rows, has_real_data={int(titles['has_real_data'].sum())}")
    print(f"market_index: {len(idx):,} rows ({idx['track'].nunique()} tracks)")


if __name__ == "__main__":
    main()
