"""Unit tests for the price pipeline pure computation functions."""

import math

from apps.worker.prices import (
    compute_hype_index,
    compute_prices,
    rolling_zscore,
    smooth_hype,
)


class TestRollingZscore:
    def test_short_window_returns_zeros(self):
        """With fewer than min_periods values, z-scores should be 0.0."""
        result = rolling_zscore([1.0, 2.0, 3.0], window=28, min_periods=7)
        assert result == [0.0, 0.0, 0.0]

    def test_sufficient_data(self):
        """With enough data, z-scores should be non-zero and within bounds."""
        values = [float(i) for i in range(30)]
        zs = rolling_zscore(values)
        assert all(-3.0 <= z <= 3.0 for z in zs)
        # After min_periods, at least some should be non-zero
        assert any(z != 0.0 for z in zs[7:])

    def test_winsorization(self):
        """Extreme values should be winsorized to [-3, 3]."""
        # Constant values then a huge spike
        values = [1.0] * 20 + [1000.0]
        zs = rolling_zscore(values, window=28, min_periods=7)
        assert zs[-1] == 3.0  # Should be capped at 3.0

    def test_constant_values(self):
        """Constant values produce z-scores of 0 (sigma forced to 1)."""
        values = [5.0] * 30
        zs = rolling_zscore(values, window=28, min_periods=7)
        assert all(z == 0.0 for z in zs)

    def test_empty_input(self):
        """Empty input returns empty output."""
        assert rolling_zscore([]) == []


class TestComputeHypeIndex:
    def test_weighted_combination(self):
        """H_t = 0.7 * z(mentions) + 0.3 * z(engagement)."""
        result = compute_hype_index([1.0, -1.0], [0.5, 0.5])
        assert abs(result[0] - (0.7 * 1.0 + 0.3 * 0.5)) < 1e-10
        assert abs(result[1] - (0.7 * -1.0 + 0.3 * 0.5)) < 1e-10

    def test_all_zeros(self):
        """Zero inputs produce zero hype index."""
        result = compute_hype_index([0.0, 0.0], [0.0, 0.0])
        assert result == [0.0, 0.0]

    def test_custom_weights(self):
        """Custom weights should be applied."""
        result = compute_hype_index([1.0], [1.0], w_mentions=0.5, w_engagement=0.5)
        assert abs(result[0] - 1.0) < 1e-10


class TestSmoothHype:
    def test_converges_to_constant(self):
        """Smoothing constant input stays constant."""
        result = smooth_hype([1.0, 1.0, 1.0, 1.0])
        assert all(abs(v - 1.0) < 1e-10 for v in result)

    def test_empty_input(self):
        """Empty input returns empty output."""
        assert smooth_hype([]) == []

    def test_smoothing_reduces_variance(self):
        """Smoothed values should be less extreme than raw values."""
        raw = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        smoothed = smooth_hype(raw)
        # The smoothed series should have smaller absolute values on average
        raw_abs_avg = sum(abs(v) for v in raw) / len(raw)
        smooth_abs_avg = sum(abs(v) for v in smoothed) / len(smoothed)
        assert smooth_abs_avg < raw_abs_avg

    def test_first_value_matches(self):
        """First smoothed value equals first raw value."""
        result = smooth_hype([5.0, 0.0, 0.0])
        assert result[0] == 5.0


class TestComputePrices:
    def test_zero_hype_stays_at_p0(self):
        """Zero hype produces P_t = P_0 for all t."""
        prices = compute_prices([0.0, 0.0, 0.0])
        assert all(abs(p - 100.0) < 1e-10 for p in prices)

    def test_positive_hype_increases_price(self):
        """Positive hype should increase price."""
        prices = compute_prices([1.0, 1.0, 1.0])
        assert all(p > 100.0 for p in prices)
        # Prices should be strictly increasing
        assert prices[0] < prices[1] < prices[2]

    def test_negative_hype_decreases_price(self):
        """Negative hype should decrease price."""
        prices = compute_prices([-1.0, -1.0, -1.0])
        assert all(p < 100.0 for p in prices)

    def test_custom_p0(self):
        """Custom starting price should be used."""
        prices = compute_prices([0.0], p0=50.0)
        assert abs(prices[0] - 50.0) < 1e-10

    def test_exponential_growth(self):
        """Price follows exponential formula."""
        prices = compute_prices([1.0, 1.0])
        expected_0 = 100.0 * math.exp(0.02 * 1.0)
        expected_1 = expected_0 * math.exp(0.02 * 1.0)
        assert abs(prices[0] - expected_0) < 1e-8
        assert abs(prices[1] - expected_1) < 1e-8

    def test_empty_input(self):
        """Empty input returns empty output."""
        assert compute_prices([]) == []
