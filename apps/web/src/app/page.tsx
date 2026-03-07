"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchTitles,
  fetchTrending,
  type Title,
  type TrendingItem,
} from "@/lib/api";
import { useWatchlist } from "@/lib/watchlist";
import { usePortfolio } from "@/lib/portfolio";

const MEDIUMS = ["manga", "manhwa", "manhua", "webtoon"] as const;
const SORT_OPTIONS = [
  { value: "name", label: "A-Z" },
  { value: "hype", label: "Hype \u2191" },
  { value: "price", label: "Price \u2191" },
];

function PriceChangeBadge({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return null;
  const isPositive = pct > 0;
  const color = isPositive
    ? "text-emerald-400 bg-emerald-400/10"
    : pct < 0
    ? "text-red-400 bg-red-400/10"
    : "text-zinc-400 bg-zinc-800";
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${color}`}>
      {isPositive ? "+" : ""}
      {pct.toFixed(1)}%
    </span>
  );
}

function TrendingCard({ item }: { item: TrendingItem }) {
  const isPositive = item.price_change_pct > 0;
  return (
    <Link
      href={`/series/${item.canonical_id}`}
      className="flex-shrink-0 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 transition-colors hover:border-amber-500/50 hover:bg-zinc-900 w-56"
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-zinc-100 truncate">
          {item.canonical_name}
        </h4>
        <span
          className={`text-xs font-medium whitespace-nowrap ${
            isPositive ? "text-emerald-400" : item.price_change_pct < 0 ? "text-red-400" : "text-zinc-400"
          }`}
        >
          {isPositive ? "+" : ""}
          {item.price_change_pct.toFixed(1)}%
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
        <span className="rounded bg-zinc-800 px-1 py-0.5">{item.medium}</span>
        <span>${item.current_price.toFixed(0)}</span>
      </div>
    </Link>
  );
}

export default function Home() {
  const [titles, setTitles] = useState<Title[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [medium, setMedium] = useState<string>("");
  const [sort, setSort] = useState("name");
  const [loading, setLoading] = useState(true);
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const { isIn, toggle: toggleWatchlist } = useWatchlist();
  const { getPosition } = usePortfolio();

  // Fetch trending on mount
  useEffect(() => {
    setTrendingLoading(true);
    fetchTrending("7d")
      .then((r) => setTrending(r.items))
      .catch(() => setTrending([]))
      .finally(() => setTrendingLoading(false));
  }, []);

  // Fetch titles with filters
  useEffect(() => {
    setLoading(true);
    fetchTitles(page, 20, search || undefined, medium || undefined, sort || undefined)
      .then((r) => {
        setTitles(r.items);
        setTotal(r.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, search, medium, sort]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold tracking-tight text-amber-400">
              HypeX
            </Link>
            <Link
              href="/watchlist"
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Watchlist
            </Link>
            <Link
              href="/portfolio"
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Portfolio
            </Link>
          </div>
          <span className="text-sm text-zinc-500">TradingView for comics hype</span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {/* Trending Section */}
        {!trendingLoading && trending.length > 0 && (
          <div className="mb-8">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Trending Now
            </h2>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
              {trending.map((item) => (
                <TrendingCard key={item.canonical_id} item={item} />
              ))}
            </div>
          </div>
        )}
        {trendingLoading && (
          <div className="mb-8">
            <div className="mb-3 h-4 w-28 animate-pulse rounded bg-zinc-800" />
            <div className="flex gap-3 overflow-x-auto pb-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="w-56 flex-shrink-0 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3"
                >
                  <div className="h-4 w-3/4 animate-pulse rounded bg-zinc-800" />
                  <div className="mt-2 flex gap-2">
                    <div className="h-3 w-12 animate-pulse rounded bg-zinc-800" />
                    <div className="h-3 w-8 animate-pulse rounded bg-zinc-800" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters & Sort */}
        <div className="mb-6 flex flex-wrap gap-4">
          <input
            type="search"
            placeholder="Search titles..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          <select
            value={medium}
            onChange={(e) => {
              setMedium(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-zinc-100 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All mediums</option>
            {MEDIUMS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-zinc-100 focus:border-amber-500 focus:outline-none"
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4"
              >
                <div className="h-5 w-3/4 animate-pulse rounded bg-zinc-800" />
                <div className="mt-2 flex gap-2">
                  <div className="h-4 w-16 animate-pulse rounded bg-zinc-800" />
                  <div className="h-4 w-10 animate-pulse rounded bg-zinc-800" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-zinc-500">
              {total} title{total !== 1 ? "s" : ""}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {titles.map((t) => (
                <div
                  key={t.canonical_id}
                  className="relative rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-amber-500/50 hover:bg-zinc-900"
                >
                  <Link
                    href={`/series/${t.canonical_id}`}
                    className="block"
                  >
                    <div className="flex items-start justify-between gap-2 pr-6">
                      <h3 className="font-semibold text-zinc-100">{t.canonical_name}</h3>
                      <PriceChangeBadge pct={t.price_change_pct} />
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                      <span className="rounded bg-zinc-800 px-1.5 py-0.5">{t.medium}</span>
                      {t.year && <span>{t.year}</span>}
                      {t.latest_price != null && (
                        <span className="text-zinc-400">${t.latest_price.toFixed(0)}</span>
                      )}
                      {getPosition(t.canonical_id) && (
                        <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-400">
                          {getPosition(t.canonical_id)!.shares.toFixed(2)} shares
                        </span>
                      )}
                    </div>
                  </Link>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      toggleWatchlist(t.canonical_id);
                    }}
                    className="absolute right-3 top-3 text-sm transition-transform hover:scale-110"
                    title={isIn(t.canonical_id) ? "Remove from watchlist" : "Add to watchlist"}
                  >
                    {isIn(t.canonical_id) ? "❤️" : "🤍"}
                  </button>
                </div>
              ))}
            </div>

            {total > 20 && (
              <div className="mt-6 flex justify-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-zinc-700 px-4 py-2 disabled:opacity-50"
                >
                  Prev
                </button>
                <span className="flex items-center px-4 text-zinc-500">
                  Page {page}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 20 >= total}
                  className="rounded border border-zinc-700 px-4 py-2 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
