# Case study — HypeX: Comics Hype Market Analytics

## Problem
Can the "hype" around a comic be measured, priced, and analyzed with the same toolkit
used for financial markets? HypeX builds a small market of 100 Korean manhwa/webtoon
titles, turns demand signals into a daily **price index**, and runs a full analyst
workflow on top: EDA, risk, a factor backtest, time-series statistics, and a dashboard.

## 1. Building the universe (data engineering)
- Pulled the title universe from the **AniList GraphQL API** (`countryOfOrigin: KR`),
  unioning an all-time-popularity sort with a current-trending sort.
- Ranked by a **balanced blend** (75% all-time popularity, magnitude-preserving log-scale;
  25% current trending) so the recognizable canon (Solo Leveling, Tower of God, Omniscient
  Reader) surfaces while currently-hot titles still rise.
- Derived cohorts for analysis: **theme** (from AniList content tags — Dungeon, Martial
  Arts, Regression, Villainess…) and **debut decade**. Raw genres were 84% "Action" and
  useless as a cohort, so I switched to the richer tag-based themes.

## 2. Two demand signals → one price model
A documented, dependency-free price model converts demand into price:
> rolling 28-day z-score (winsorized ±3) → hype index `H = 0.7·z(mentions)+0.3·z(eng)`
> → exponential smoothing → `P_t = P_{t-1}·exp(0.02·Hs_t)`, `P₀ = 100`.

- **Track 1 — synthetic** (all 100): a seeded daily signal whose baseline scales with real
  AniList popularity and whose 2-year drift is driven by real `trending`, plus weekly
  release spikes, noise, and an idiosyncratic random walk so returns are realistically
  *mostly unpredictable*.
- **Track 2 — real** (top 30): actual **Google Trends** weekly search interest, fed through
  the same model. Ambiguous titles got disambiguating queries ("Bastard webtoon");
  `Sweet Home` is kept but flagged (its Netflix adaptation contaminates search).

## 3. Analysis
- **EDA** (Python): log-returns, annualized volatility (median ≈46%), a near-zero mean
  cross-title correlation (genuine dispersion), risk-return scatter, and cohort returns by
  theme/decade. A synthetic-vs-real check confirms the real signal carries independent
  information (final-return correlation ≈0.17).
- **Factor backtest** (Python): weekly-rebalanced, cross-sectional, strictly anti-lookahead
  (signal at *t*, returns from *t+1*). Tested momentum vs reversal as long-short decile
  books against an equal-weight benchmark.
- **Statistics** (base R): ARIMA forecast of the index (order by AIC grid search), a
  **GARCH(1,1) fit by maximum likelihood from scratch** via `optim`, and an Engle-Granger
  cointegration test (hand-rolled ADF) to screen for a pairs trade.

## 4. Findings
- **Hype mean-reverts.** Momentum loses; the contrarian reversal book wins (Sharpe +2.2 vs
  the benchmark's ~0). Spikes fade and cooled titles bounce — a clear regime read.
- **Volatility clusters.** GARCH persistence (α+β) ≈ **0.92**, the textbook signature of
  financial-style volatility clustering, even in this hype market.
- **A tradeable pair exists.** Engle-Granger flagged a cointegrated pair (corr 0.95, ADF
  −4.46) — a pairs-trade candidate (would need out-of-sample validation; it was selected by
  screening the max-correlation pair, so treat as a lead, not a result).
- The **real** search-interest market cooled to ~94 over two years — most of these
  (mostly older) titles are past their search peak.

## 5. Analytical decisions & bugs caught (the interesting part)
- **Webtoon labeling**: AniList has no "Webtoon" tag — the format is encoded as "Long
  Strip" + "Full Color". Caught when 100% of titles mislabeled as print manhwa.
- **Ranking blend**: an early percentile blend buried Solo Leveling at #24; switched to a
  magnitude-preserving log blend so the canon ranks correctly.
- **Real-price blow-up**: pricing the daily forward-filled Trends series compounded the
  exponential 7×/week (prices → 0.6 or 896). Fixed by pricing at the native **weekly**
  cadence, then forward-filling prices.
- **Backtest artifact**: an initial −16 Sharpe revealed the synthetic price was nearly
  noise-free and mechanically mean-reverting; added an idiosyncratic random walk (and
  de-meaned it to kill a log-normal drift) so backtests are realistic.

## 6. Limitations
Prices are a modeled index, not traded values. Backtest magnitudes are inflated by
synthetic mechanics (the methodology is the deliverable). Real data is weekly and relative
(Google Trends), and limited to 30 titles by rate limits.

## Résumé bullets
- Built an end-to-end analytics pipeline (Python, pandas) ingesting the **AniList GraphQL**
  and **Google Trends** APIs for 100 titles, with entity resolution, a star-schema model,
  and idempotent/resumable extraction under rate limits.
- Engineered a demand→price model and ran **time-series EDA** — returns, annualized
  volatility, Sharpe, drawdown, and a 100-asset correlation study.
- Backtested a cross-sectional **hype factor** (momentum vs reversal) with strict
  anti-lookahead and long-short construction; identified the market as reversion-driven.
- Authored a **base-R** statistical report: ARIMA forecasting, a **GARCH(1,1) MLE from
  scratch**, and Engle-Granger cointegration screening.
- Delivered an interactive **Plotly** dashboard plus a **PowerBI/Tableau** build guide
  (DAX measures, 5-page spec).

## Tools
Python (pandas, numpy, statsmodels, plotly, seaborn, pytrends) · R (base: arima, optim,
lm) · Jupyter/jupytext · PowerBI/Tableau · Git · PostgreSQL (platform) · FastAPI/Next.js
(platform).
