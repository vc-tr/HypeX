"""HypeX FastAPI application."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from hypex_core import load_registry, resolve_mention

from .db import (
    get_db,
    get_metrics_series,
    get_price_series,
    get_series,
    get_top_gainers,
    get_top_losers,
    get_trending,
    list_titles,
    list_titles_sorted,
)
from .models import (
    MetricPointOut,
    PricePointOut,
    ResolveCandidateOut,
    ResolveRequest,
    ResolveResponse,
    SeriesDetailResponse,
    SeriesResponse,
    TitleOut,
    TitlesListResponse,
    TrendingItemOut,
    TrendingResponse,
)

app = FastAPI(
    title="HypeX API",
    description="TradingView for comics hype — titles, series, prices",
    version="0.1.0",
    tags=["titles", "resolve", "series"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health/db", tags=["health"])
def health_db():
    """Check database connectivity."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


# Load registry once at startup (for resolve when DB has no titles yet)
_REGISTRY: tuple[list, list] | None = None


def _get_registry():
    global _REGISTRY
    if _REGISTRY is None:
        root = Path(__file__).resolve().parent.parent.parent.parent
        titles_path = root / "data" / "registry" / "titles.csv"
        aliases_path = root / "data" / "registry" / "aliases.json"
        _REGISTRY = load_registry(str(titles_path), str(aliases_path))
    return _REGISTRY


def _title_to_out(row: dict) -> TitleOut:
    aliases = row.get("aliases") or []
    if isinstance(aliases, str):
        import json
        aliases = json.loads(aliases) if aliases else []
    # Compute price change % if we have latest and previous price
    price_change_pct = None
    latest_price = row.get("latest_price")
    prev_price = row.get("prev_price")
    if latest_price is not None and prev_price is not None and prev_price > 0:
        price_change_pct = round((latest_price - prev_price) / prev_price * 100, 2)
    return TitleOut(
        canonical_id=row["canonical_id"],
        canonical_name=row["canonical_name"],
        medium=row["medium"],
        language=row["language"],
        aliases=aliases,
        platform=row.get("platform"),
        year=row.get("year"),
        latest_price=round(float(latest_price), 2) if latest_price is not None else None,
        latest_hype=round(float(row["latest_hype"]), 4) if row.get("latest_hype") is not None else None,
        price_change_pct=price_change_pct,
    )


@app.get("/titles", tags=["titles"], response_model=TitlesListResponse)
def list_titles_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by name or alias"),
    medium: str | None = Query(None, description="Filter by medium"),
    sort: str = Query("name", description="Sort by: name, hype, price"),
):
    """List titles with pagination and optional sorting."""
    try:
        with get_db() as conn:
            rows, total = list_titles_sorted(
                conn, page=page, limit=limit, search=search, medium=medium, sort=sort
            )
            return TitlesListResponse(
                items=[_title_to_out(r) for r in rows],
                total=total,
                page=page,
                limit=limit,
            )
    except Exception:
        # Fallback to registry if DB not populated
        titles, _ = _get_registry()
        filtered = titles
        if search:
            search_lower = search.lower()
            filtered = [
                t
                for t in filtered
                if search_lower in t.canonical_name.lower()
                or any(search_lower in a.lower() for a in t.aliases)
            ]
        if medium:
            filtered = [t for t in filtered if t.medium == medium]
        total = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        items = filtered[start:end]
        return TitlesListResponse(
            items=[
                TitleOut(
                    canonical_id=t.canonical_id,
                    canonical_name=t.canonical_name,
                    medium=t.medium,
                    language=t.language,
                    aliases=t.aliases,
                    platform=t.platform,
                    year=t.year,
                )
                for t in items
            ],
            total=total,
            page=page,
            limit=limit,
        )


@app.post("/resolve", tags=["resolve"], response_model=ResolveResponse)
def resolve_endpoint(body: ResolveRequest):
    """Resolve text to candidate titles."""
    titles, aliases = _get_registry()
    candidates = resolve_mention(body.text, titles, aliases)
    return ResolveResponse(
        candidates=[
            ResolveCandidateOut(
                canonical_id=c.canonical_id,
                score=c.score,
                match_type=c.match_type,
            )
            for c in candidates
        ]
    )


@app.get("/trending", tags=["discovery"], response_model=TrendingResponse)
def trending_endpoint(
    period: str = Query("7d", description="Period: 7d, 14d, 30d"),
):
    """Get top 10 titles by hype change."""
    try:
        with get_db() as conn:
            rows = get_trending(conn, period=period)
            return TrendingResponse(
                items=[TrendingItemOut(**r) for r in rows],
                period=period,
            )
    except Exception:
        return TrendingResponse(items=[], period=period)


@app.get("/top-gainers", tags=["discovery"], response_model=TrendingResponse)
def top_gainers_endpoint(
    period: str = Query("7d", description="Period: 7d, 14d, 30d"),
):
    """Get top 10 titles by price % increase."""
    try:
        with get_db() as conn:
            rows = get_top_gainers(conn, period=period)
            return TrendingResponse(
                items=[TrendingItemOut(**r) for r in rows],
                period=period,
            )
    except Exception:
        return TrendingResponse(items=[], period=period)


@app.get("/top-losers", tags=["discovery"], response_model=TrendingResponse)
def top_losers_endpoint(
    period: str = Query("7d", description="Period: 7d, 14d, 30d"),
):
    """Get top 10 titles by price % decrease."""
    try:
        with get_db() as conn:
            rows = get_top_losers(conn, period=period)
            return TrendingResponse(
                items=[TrendingItemOut(**r) for r in rows],
                period=period,
            )
    except Exception:
        return TrendingResponse(items=[], period=period)


@app.get("/series/{canonical_id}", tags=["series"], response_model=SeriesDetailResponse)
def get_series_endpoint(canonical_id: str):
    """Get title info, price series, and daily metrics."""
    titles, _ = _get_registry()
    title_obj = next((t for t in titles if t.canonical_id == canonical_id), None)
    if title_obj is None:
        try:
            with get_db() as conn:
                row = get_series(conn, canonical_id)
                if row:
                    title_out = _title_to_out(row)
                else:
                    raise HTTPException(status_code=404, detail="Title not found")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=404, detail="Title not found")
    else:
        title_out = TitleOut(
            canonical_id=title_obj.canonical_id,
            canonical_name=title_obj.canonical_name,
            medium=title_obj.medium,
            language=title_obj.language,
            aliases=title_obj.aliases,
            platform=title_obj.platform,
            year=title_obj.year,
        )

    prices: list[PricePointOut] = []
    metrics: list[MetricPointOut] = []
    try:
        with get_db() as conn:
            price_rows = get_price_series(conn, canonical_id)
            prices = [
                PricePointOut(date=r["date"], hype_index=r["hype_index"], price=r["price"])
                for r in price_rows
            ]
            metric_rows = get_metrics_series(conn, canonical_id)
            metrics = [
                MetricPointOut(date=r["date"], metric_name=r["metric_name"], value=r["value"])
                for r in metric_rows
            ]
    except Exception:
        pass

    return SeriesDetailResponse(title=title_out, prices=prices, metrics=metrics)
