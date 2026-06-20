"""Tests for the analytics price-index model (analytics/pipeline/pricing.py).

Pure-math model, so these run with no external data or dependencies.
"""

import math

from analytics.pipeline.pricing import (
    compute_hype_index,
    compute_prices,
    price_real_series,
    rolling_zscore,
    smooth_hype,
)


def test_rolling_zscore_zero_before_min_periods():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    z = rolling_zscore(vals, window=28, min_periods=7)
    assert z == [0.0] * len(vals)  # min_periods never reached


def test_rolling_zscore_winsorized_to_three():
    vals = [10.0] * 10 + [1000.0]  # flat then extreme spike
    z = rolling_zscore(vals, window=28, min_periods=3)
    assert all(-3.0 <= zi <= 3.0 for zi in z)
    assert z[-1] == 3.0  # spike clamps to +3


def test_rolling_zscore_constant_series_is_zero():
    z = rolling_zscore([5.0] * 20, min_periods=3)
    assert all(abs(zi) < 1e-9 for zi in z)  # zero variance => z = 0


def test_compute_hype_index_default_weights():
    assert compute_hype_index([1.0, 0.0], [0.0, 1.0]) == [0.7, 0.3]


def test_smooth_hype_constant_input_is_stable():
    hs = smooth_hype([1.0, 1.0, 1.0], alpha=0.5)
    assert hs[0] == 1.0
    assert all(abs(x - 1.0) < 1e-9 for x in hs)


def test_smooth_hype_empty():
    assert smooth_hype([]) == []


def test_compute_prices_compounds_with_sign():
    up = compute_prices([1.0, 1.0, 1.0], p0=100.0, sensitivity=0.02)
    down = compute_prices([-1.0, -1.0, -1.0], p0=100.0, sensitivity=0.02)
    assert all(p > 0 for p in up)
    assert up[-1] > up[0]      # positive hype compounds upward
    assert down[-1] < down[0]  # negative hype compounds downward


def test_compute_prices_matches_formula():
    hs = [0.5, -0.2]
    p = compute_prices(hs, p0=100.0, sensitivity=0.02)
    expected0 = 100.0 * math.exp(0.02 * 0.5)
    expected1 = expected0 * math.exp(0.02 * -0.2)
    assert abs(p[0] - expected0) < 1e-9
    assert abs(p[1] - expected1) < 1e-9


def test_price_real_series_shapes_and_positive():
    weekly = [10.0, 12.0, 11.0, 13.0, 15.0, 14.0]
    hs, prices = price_real_series(weekly, window=4, min_periods=2)
    assert len(hs) == len(weekly)
    assert len(prices) == len(weekly)
    assert all(p > 0 for p in prices)
