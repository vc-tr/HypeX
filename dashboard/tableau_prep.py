"""Prepare Tableau-friendly flat files with metrics pre-computed and dimensions
denormalized in — so the dashboard is pure drag-and-drop (no calculated fields,
no relationships to wire up in the GUI).

  tableau_prices.csv  date, canonical_id, title, theme, decade, track, price   (the fact)
  tableau_titles.csv  per-title: total_return%, ann_vol, mean_return%, theme, decade,
                      popularity, has_real_data   (for scatter / movers / cohorts)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

EXPORTS = Path(__file__).resolve().parent.parent / "analytics" / "data" / "exports"

prices = pd.read_csv(EXPORTS / "prices_all.csv", parse_dates=["date"])
titles = pd.read_csv(EXPORTS / "titles_dim.csv")
dim = titles.set_index("canonical_id")

# fact: prices with title/theme/decade denormalized in (both tracks)
fact = prices.merge(
    titles[["canonical_id", "canonical_name", "theme", "decade"]], on="canonical_id", how="left"
).rename(columns={"canonical_name": "title"})
fact[["date", "canonical_id", "title", "theme", "decade", "track", "price"]].to_csv(
    EXPORTS / "tableau_prices.csv", index=False)

# per-title metrics from the synthetic track
syn = prices[prices.track == "synthetic"]
wide = syn.pivot(index="date", columns="canonical_id", values="price").sort_index()
rets = np.log(wide / wide.shift(1))
metrics = pd.DataFrame({
    "total_return_pct": (wide.iloc[-1] / wide.iloc[0] - 1) * 100,
    "ann_vol": rets.std() * np.sqrt(365),
    "mean_return_pct": rets.mean() * 365 * 100,
}).round(3)
out = (metrics.join(dim[["canonical_name", "theme", "decade", "popularity", "has_real_data"]])
       .reset_index().rename(columns={"canonical_name": "title"}))
out.to_csv(EXPORTS / "tableau_titles.csv", index=False)

print(f"tableau_prices.csv: {len(fact):,} rows")
print(f"tableau_titles.csv: {len(out)} rows, cols = {list(out.columns)}")
