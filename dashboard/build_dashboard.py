"""Build a self-contained interactive HTML dashboard (Plotly) from the exports.

This is the working, openable proxy for the PowerBI/Tableau dashboard — same data
model, same visuals — so the design is provable in-repo. See
POWERBI_TABLEAU_GUIDE.md to rebuild it natively in PowerBI or Tableau.

  python dashboard/build_dashboard.py  ->  dashboard/hypex_dashboard.html
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

HERE = Path(__file__).resolve().parent
EXPORTS = HERE.parent / "analytics" / "data" / "exports"

prices = pd.read_csv(EXPORTS / "prices_all.csv", parse_dates=["date"])
titles = pd.read_csv(EXPORTS / "titles_dim.csv")
index = pd.read_csv(EXPORTS / "market_index.csv", parse_dates=["date"])
syn = prices[prices.track == "synthetic"]
real = prices[prices.track == "real"]
name = dict(zip(titles.canonical_id, titles.canonical_name))
wide = syn.pivot(index="date", columns="canonical_id", values="price").sort_index()
PASTEL = dict(template="plotly_white", margin=dict(l=60, r=30, t=60, b=40), height=460)
figs = []

# 1. Market index — synthetic vs real
f = go.Figure()
for trk, g in index.groupby("track"):
    f.add_scatter(x=g.date, y=g.index_level, name=f"{trk} index", mode="lines")
f.add_hline(y=100, line_dash="dash", line_color="gray")
f.update_layout(title="HypeX Equal-Weight Market Index", yaxis_title="index (P₀=100)", **PASTEL)
figs.append(("Market overview", f))

# 2. Top / bottom movers (synthetic 2-yr return)
tot = (wide.iloc[-1] / wide.iloc[0] - 1) * 100
mv = pd.concat([tot.nlargest(10), tot.nsmallest(10)]).sort_values()
f = go.Figure(go.Bar(x=mv.values, y=[name.get(c, c) for c in mv.index], orientation="h",
                     marker_color=["seagreen" if v > 0 else "indianred" for v in mv.values]))
f.update_layout(title="Biggest movers — 2-year return (%)", xaxis_title="%", **{**PASTEL, "height": 560})
figs.append(("Top & bottom movers", f))

# 3. Per-title: synthetic vs real (dropdown over the 30 real titles)
real_wide = real.pivot(index="date", columns="canonical_id", values="price").sort_index()
real_ids = [c for c in real_wide.columns if c in wide.columns]
f = go.Figure()
for i, cid in enumerate(real_ids):
    f.add_scatter(x=wide.index, y=wide[cid], name="synthetic", line_color="#888",
                  visible=(i == 0))
    f.add_scatter(x=real_wide.index, y=real_wide[cid], name="real (Trends)", line_color="#1f77b4",
                  visible=(i == 0))
buttons = []
for i, cid in enumerate(real_ids):
    vis = [False] * (2 * len(real_ids))
    vis[2 * i] = vis[2 * i + 1] = True
    buttons.append(dict(label=name.get(cid, cid)[:34], method="update",
                        args=[{"visible": vis}, {"title": f"Price — {name.get(cid, cid)} (synthetic vs real)"}]))
f.update_layout(title=f"Price — {name.get(real_ids[0], real_ids[0])} (synthetic vs real)",
                updatemenus=[dict(buttons=buttons, x=1.0, xanchor="right", y=1.16)],
                yaxis_title="price", **PASTEL)
figs.append(("Title drill-down", f))

# 4. Risk-return scatter colored by theme
rets = np.log(wide / wide.shift(1))
rr = pd.DataFrame({"vol": rets.std() * np.sqrt(365), "ret": rets.mean() * 365})
rr = rr.join(titles.set_index("canonical_id")[["canonical_name", "theme", "popularity"]])
f = go.Figure()
for th, g in rr.groupby("theme"):
    if len(g) >= 3:
        f.add_scatter(x=g.vol, y=g.ret * 100, mode="markers", name=th, text=g.canonical_name,
                      marker=dict(size=9, opacity=0.75))
f.update_layout(title="Risk vs return by theme (annualized)", xaxis_title="volatility",
                yaxis_title="mean return (%)", **{**PASTEL, "height": 520})
figs.append(("Risk & return", f))

# 5. Correlation heatmap (top 20 by popularity)
top20 = titles.sort_values("popularity", ascending=False).canonical_id.head(20)
top20 = [c for c in top20 if c in rets.columns]
corr = rets[top20].corr()
labels = [name.get(c, c)[:16] for c in top20]
f = go.Figure(go.Heatmap(z=corr.values, x=labels, y=labels, zmid=0, colorscale="RdBu_r",
                         zmin=-0.4, zmax=0.4))
f.update_layout(title="Return correlation — top 20 titles", **{**PASTEL, "height": 620})
figs.append(("Correlation", f))

# 6. Cohort returns by theme
by_theme = rr.groupby("theme").ret.agg(["mean", "count"]).query("count >= 3").sort_values("mean")
f = go.Figure(go.Bar(x=by_theme["mean"] * 100, y=by_theme.index, orientation="h", marker_color="teal"))
f.update_layout(title="Mean 2-yr return by theme cohort (%)", xaxis_title="%", **PASTEL)
figs.append(("Cohort analysis", f))

# ── assemble single HTML ────────────────────────────────────────────────
blocks = []
for i, (section, fig) in enumerate(figs):
    inner = pio.to_html(fig, include_plotlyjs=(True if i == 0 else False), full_html=False,
                        config={"displayModeBar": False})
    blocks.append(f'<section><h2>{section}</h2>{inner}</section>')

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>HypeX — Comics Hype Market Analytics</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#222}}
 header{{background:#1f2a44;color:#fff;padding:26px 40px}}
 header h1{{margin:0;font-size:24px}} header p{{margin:6px 0 0;opacity:.85}}
 section{{background:#fff;margin:22px auto;max-width:1080px;padding:10px 22px 18px;
   border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
 h2{{font-size:16px;color:#1f2a44;border-bottom:1px solid #eee;padding-bottom:8px}}
 footer{{text-align:center;color:#888;padding:24px;font-size:12px}}
</style></head><body>
<header><h1>HypeX — Comics Hype Market Analytics</h1>
<p>100 Korean manhwa/webtoon titles · synthetic + real (Google Trends) demand priced as a market · 2 years daily</p></header>
{''.join(blocks)}
<footer>Interactive proxy of the PowerBI/Tableau dashboard · built from analytics/data/exports · prices are a modeled hype index, not real market prices</footer>
</body></html>"""

out = HERE / "hypex_dashboard.html"
out.write_text(html, encoding="utf-8")
print(f"Wrote {out}  ({out.stat().st_size // 1024} KB, {len(figs)} panels)")
