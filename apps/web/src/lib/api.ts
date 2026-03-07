const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Title {
  canonical_id: string;
  canonical_name: string;
  medium: string;
  language: string;
  aliases: string[];
  platform?: string;
  year?: number;
  latest_price?: number | null;
  latest_hype?: number | null;
  price_change_pct?: number | null;
}

export interface TitlesResponse {
  items: Title[];
  total: number;
  page: number;
  limit: number;
}

export interface PricePoint {
  date: string;
  hype_index: number;
  price: number;
}

export interface MetricPoint {
  date: string;
  metric_name: string;
  value: number;
}

export interface SeriesResponse {
  title: Title;
  prices: PricePoint[];
  metrics: MetricPoint[];
}

export interface TrendingItem {
  canonical_id: string;
  canonical_name: string;
  medium: string;
  price_change_pct: number;
  hype_change: number;
  current_price: number;
  current_hype: number;
}

export interface TrendingResponse {
  items: TrendingItem[];
  period: string;
}

export interface ResolveCandidate {
  canonical_id: string;
  score: number;
  match_type: string;
}

export async function fetchTitles(
  page = 1,
  limit = 20,
  search?: string,
  medium?: string,
  sort?: string
): Promise<TitlesResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (search) params.set("search", search);
  if (medium) params.set("medium", medium);
  if (sort) params.set("sort", sort);
  const res = await fetch(`${API_URL}/titles?${params}`);
  if (!res.ok) throw new Error("Failed to fetch titles");
  return res.json();
}

export async function fetchSeries(canonicalId: string): Promise<SeriesResponse> {
  const res = await fetch(`${API_URL}/series/${encodeURIComponent(canonicalId)}`);
  if (!res.ok) throw new Error("Failed to fetch series");
  return res.json();
}

export async function fetchTrending(period = "7d"): Promise<TrendingResponse> {
  const res = await fetch(`${API_URL}/trending?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error("Failed to fetch trending");
  return res.json();
}

export async function fetchTopGainers(period = "7d"): Promise<TrendingResponse> {
  const res = await fetch(`${API_URL}/top-gainers?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error("Failed to fetch top gainers");
  return res.json();
}

export async function fetchTopLosers(period = "7d"): Promise<TrendingResponse> {
  const res = await fetch(`${API_URL}/top-losers?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error("Failed to fetch top losers");
  return res.json();
}

export async function resolveText(text: string): Promise<{ candidates: ResolveCandidate[] }> {
  const res = await fetch(`${API_URL}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to resolve");
  return res.json();
}
