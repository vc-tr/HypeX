# Building the HypeX dashboard in PowerBI / Tableau

`hypex_dashboard.html` (run `build_dashboard.py`) is a working interactive proxy.
This guide rebuilds the same thing natively. Budget ~2 hours.

## 1. Connect the data
Point the tool at `analytics/data/exports/` (Get Data → Text/CSV, or Tableau → Text file):

| File | Role | Grain |
|------|------|-------|
| `prices_all.csv` | **fact** — price & hype_index | date × title × track |
| `titles_dim.csv` | **dimension** — name, theme, decade, popularity, `has_real_data` | one row per title |
| `market_index.csv` | pre-aggregated equal-weight index | date × track |
| `metrics.csv` / `metrics_real.csv` | optional raw signals | date × title |

## 2. Model (relationships)
- `titles_dim[canonical_id]` **1 — ∗** `prices_all[canonical_id]`
- Mark a **Date table** on `prices_all[date]` (PowerBI: *Mark as date table*) for time intelligence.
- `track` (synthetic / real) is a slicer/filter field on `prices_all`.

## 3. DAX measures (PowerBI)
```DAX
Latest Price   = CALCULATE ( MAX(prices_all[price]), LASTDATE(prices_all[date]) )
Start Price    = CALCULATE ( MAX(prices_all[price]), FIRSTDATE(prices_all[date]) )
Total Return % = DIVIDE([Latest Price] - [Start Price], [Start Price])

Daily Return =
VAR d = MAX(prices_all[date])
VAR p0 = CALCULATE(MAX(prices_all[price]), prices_all[date] = d - 1)
RETURN DIVIDE(MAX(prices_all[price]) - p0, p0)

MA 28 = AVERAGEX ( DATESINPERIOD(prices_all[date], MAX(prices_all[date]), -28, DAY), [Latest Price] )

Ann. Volatility =                                  -- stdev of daily returns × √365
VAR rets = ADDCOLUMNS(VALUES(prices_all[date]), "r", [Daily Return])
RETURN STDEVX.P(rets, [r]) * SQRT(365)

Sharpe = DIVIDE( AVERAGEX(VALUES(prices_all[date]),[Daily Return]) * 365, [Ann. Volatility] )

Title Rank = RANKX ( ALL(titles_dim[canonical_name]), [Total Return %],, DESC )
```

## 4. Tableau equivalents
- **Daily Return**: `(ZN(SUM([price])) - LOOKUP(ZN(SUM([price])),-1)) / LOOKUP(ZN(SUM([price])),-1)` (table calc along date).
- **Total Return**: `(LAST_VALUE(SUM([price])) - FIRST_VALUE(SUM([price]))) / FIRST_VALUE(...)`.
- **Volatility**: `WINDOW_STDEV([Daily Return]) * SQRT(365)`; **Sharpe** = `WINDOW_AVG([Daily Return])*365 / [Volatility]`.
- Use `theme`, `decade`, `track` as filters/colors.

## 5. Pages (match the Plotly proxy)
1. **Market Overview** — `market_index.csv` line (synthetic vs real, slicer on `track`); KPI cards (# titles, [Latest Price] of index, top gainer/loser via [Title Rank]); top/bottom-10 movers bar (`[Total Return %]`).
2. **Title Drill-down** — slicer on `canonical_name`; line of `price` with `track` color (synthetic vs real for the 30 `has_real_data` titles); `MA 28`; KPI cards for return/vol.
3. **Cohort Analysis** — bar of avg `[Total Return %]` by `theme`; by `decade`; theme × decade matrix heatmap.
4. **Risk & Correlation** — scatter `[Ann. Volatility]` (x) vs mean return (y), dot = title, color = `theme`, size = `popularity`; volatility ranking bar.
5. **Factor Backtest** — import `analytics/reports/backtest_findings.md` numbers as cards; embed `reports/figures/backtest.png`, or recreate the equity curves from a small exported returns table.

## 6. Polish
Title "HypeX — Comics Hype Market Analytics"; footnote: *prices are a modeled hype
index, not real market prices*. Export 4–5 page screenshots into
`analytics/reports/figures/` for the README. (Tableau Public also gives a shareable
live link — great on a résumé.)
