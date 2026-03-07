"""Pydantic models for API."""

from typing import Optional

from pydantic import BaseModel, Field


class TitleOut(BaseModel):
    """Title in list/detail response."""

    canonical_id: str
    canonical_name: str
    medium: str
    language: str
    aliases: list[str] = Field(default_factory=list)
    platform: Optional[str] = None
    year: Optional[int] = None
    latest_price: Optional[float] = None
    latest_hype: Optional[float] = None
    price_change_pct: Optional[float] = None


class ResolveRequest(BaseModel):
    """Request body for resolve endpoint."""

    text: str = Field(..., min_length=1, description="Text to resolve to title(s)")


class ResolveCandidateOut(BaseModel):
    """Single resolve candidate."""

    canonical_id: str
    score: float
    match_type: str


class ResolveResponse(BaseModel):
    """Response for resolve endpoint."""

    candidates: list[ResolveCandidateOut]


class PricePointOut(BaseModel):
    """Single price/hype data point."""

    date: str
    hype_index: float
    price: float


class SeriesResponse(BaseModel):
    """Response for series detail."""

    title: TitleOut
    prices: list[PricePointOut] = Field(default_factory=list)


class TitlesListResponse(BaseModel):
    """Paginated titles list."""

    items: list[TitleOut]
    total: int
    page: int
    limit: int


class TrendingItemOut(BaseModel):
    """Item in trending / top gainers / top losers responses."""

    canonical_id: str
    canonical_name: str
    medium: str
    price_change_pct: float = 0
    hype_change: float = 0
    current_price: float = 0
    current_hype: float = 0


class TrendingResponse(BaseModel):
    """Response for trending endpoints."""

    items: list[TrendingItemOut]
    period: str


class MetricPointOut(BaseModel):
    """Single metric data point."""

    date: str
    metric_name: str
    value: float


class SeriesDetailResponse(BaseModel):
    """Extended series response with metrics."""

    title: TitleOut
    prices: list[PricePointOut] = Field(default_factory=list)
    metrics: list[MetricPointOut] = Field(default_factory=list)
