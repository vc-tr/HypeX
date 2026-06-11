"""Pure price math — mirrors apps/worker/prices.py (the HypeX v1 price spec),
kept dependency-free (no psycopg / Postgres) so the analytics pipeline reproduces
end-to-end from CSVs alone.

Spec:
  z      = rolling 28-day z-score (min 7 periods), winsorized to [-3, 3]
  H_t    = 0.7 * z(mentions) + 0.3 * z(engagement)
  Hs_t   = 0.7 * H_t + 0.3 * Hs_{t-1}          (exponential smoothing)
  P_t    = P_{t-1} * exp(0.02 * Hs_t),  P_0 = 100
"""

from __future__ import annotations

import math
from statistics import mean, stdev


def rolling_zscore(values: list[float], window: int = 28, min_periods: int = 7) -> list[float]:
    """Rolling z-scores winsorized to [-3, 3]; 0.0 until min_periods seen."""
    zscores: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = values[start : i + 1]
        if len(window_vals) < min_periods:
            zscores.append(0.0)
            continue
        mu = mean(window_vals)
        sigma = stdev(window_vals) if len(window_vals) > 1 else 1.0
        if sigma == 0:
            sigma = 1.0
        z = (values[i] - mu) / sigma
        zscores.append(max(-3.0, min(3.0, z)))
    return zscores


def compute_hype_index(z_mentions, z_engagement, w_mentions=0.7, w_engagement=0.3):
    """H_t = w_mentions * z(mentions) + w_engagement * z(engagement)."""
    return [w_mentions * zm + w_engagement * ze for zm, ze in zip(z_mentions, z_engagement)]


def smooth_hype(h_values: list[float], alpha: float = 0.7) -> list[float]:
    """Hs_t = alpha * H_t + (1 - alpha) * Hs_{t-1}."""
    if not h_values:
        return []
    smoothed = [h_values[0]]
    for i in range(1, len(h_values)):
        smoothed.append(alpha * h_values[i] + (1 - alpha) * smoothed[i - 1])
    return smoothed


def compute_prices(hs_values: list[float], p0: float = 100.0, sensitivity: float = 0.02):
    """P_t = P_{t-1} * exp(sensitivity * Hs_t), P_0 = p0."""
    if not hs_values:
        return []
    prices = [p0 * math.exp(sensitivity * hs_values[0])]
    for i in range(1, len(hs_values)):
        prices.append(prices[i - 1] * math.exp(sensitivity * hs_values[i]))
    return prices
