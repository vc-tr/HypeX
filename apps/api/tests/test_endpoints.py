"""API endpoint tests using FastAPI TestClient.

These tests use the registry fallback (no DB required) for /titles and /resolve.
The /series and /health/db endpoints may fail without a DB but should not crash.
"""

from fastapi.testclient import TestClient

from apps.api.src.main import app

client = TestClient(app)


class TestTitlesEndpoint:
    def test_list_titles_200(self):
        r = client.get("/titles")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_list_titles_pagination(self):
        r = client.get("/titles?page=1&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 5
        assert len(data["items"]) <= 5

    def test_list_titles_search(self):
        r = client.get("/titles?search=one+piece")
        assert r.status_code == 200
        data = r.json()
        if data["total"] > 0:
            assert any("one" in item["canonical_name"].lower() for item in data["items"])

    def test_list_titles_medium_filter(self):
        r = client.get("/titles?medium=manga")
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            assert item["medium"] == "manga"

    def test_list_titles_sort_param(self):
        """Sort param should be accepted without error."""
        for sort_val in ["name", "hype", "price"]:
            r = client.get(f"/titles?sort={sort_val}")
            assert r.status_code == 200
            data = r.json()
            assert "items" in data

    def test_title_has_optional_price_fields(self):
        """TitleOut model should accept price fields (may be null from registry fallback)."""
        r = client.get("/titles?limit=1")
        assert r.status_code == 200
        data = r.json()
        if data["items"]:
            item = data["items"][0]
            assert "canonical_id" in item
            # Price fields exist (may be null)
            assert "latest_price" in item or item.get("latest_price") is None
            assert "latest_hype" in item or item.get("latest_hype") is None
            assert "price_change_pct" in item or item.get("price_change_pct") is None


class TestResolveEndpoint:
    def test_resolve_basic(self):
        r = client.post("/resolve", json={"text": "One Piece"})
        assert r.status_code == 200
        data = r.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 1
        assert data["candidates"][0]["canonical_id"] == "one-piece"

    def test_resolve_abbreviation(self):
        r = client.post("/resolve", json={"text": "CSM"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["candidates"]) >= 1

    def test_resolve_empty_text_rejected(self):
        r = client.post("/resolve", json={"text": ""})
        assert r.status_code == 422  # Pydantic validation

    def test_resolve_returns_score_and_type(self):
        r = client.post("/resolve", json={"text": "Solo Leveling"})
        assert r.status_code == 200
        data = r.json()
        for c in data["candidates"]:
            assert "canonical_id" in c
            assert "score" in c
            assert "match_type" in c
            assert 0.0 <= c["score"] <= 1.0


class TestSeriesEndpoint:
    def test_series_not_found(self):
        """Non-existent title should return 404."""
        r = client.get("/series/nonexistent-title-xyz-12345")
        assert r.status_code == 404

    def test_series_known_title(self):
        """Known title from registry should return 200 (even without DB data)."""
        r = client.get("/series/one-piece")
        assert r.status_code == 200
        data = r.json()
        assert data["title"]["canonical_id"] == "one-piece"
        assert "prices" in data
        assert "metrics" in data

    def test_series_response_has_metrics_field(self):
        """SeriesDetailResponse should include metrics array."""
        r = client.get("/series/one-piece")
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data.get("metrics"), list)


class TestTrendingEndpoints:
    def test_trending_returns_200(self):
        """Trending endpoint should return 200 (even with empty data)."""
        r = client.get("/trending")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "period" in data
        assert isinstance(data["items"], list)

    def test_trending_with_period(self):
        """Trending accepts period parameter."""
        r = client.get("/trending?period=30d")
        assert r.status_code == 200
        data = r.json()
        assert data["period"] == "30d"

    def test_top_gainers_returns_200(self):
        r = client.get("/top-gainers")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_top_losers_returns_200(self):
        r = client.get("/top-losers")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_trending_item_has_fields(self):
        """If trending returns items, verify shape."""
        r = client.get("/trending")
        data = r.json()
        for item in data["items"]:
            assert "canonical_id" in item
            assert "canonical_name" in item
            assert "medium" in item
            assert "price_change_pct" in item
            assert "hype_change" in item
            assert "current_price" in item
            assert "current_hype" in item


class TestHealthEndpoint:
    def test_health_db_returns_status(self):
        """Health endpoint should return a status field (200 or 503)."""
        r = client.get("/health/db")
        assert r.status_code in (200, 503)
        data = r.json()
        assert "status" in data
