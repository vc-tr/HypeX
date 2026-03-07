"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchSeries, type PricePoint } from "@/lib/api";
import { useWatchlist } from "@/lib/watchlist";

interface WatchlistEntry {
  id: string;
  name: string;
  medium: string;
  latestPrice?: number;
  priceChange?: number;
  loading: boolean;
}

export default function WatchlistPage() {
  const { ids, remove } = useWatchlist();
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ids.length) {
      setEntries([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    // Fetch series data for all watchlisted IDs
    Promise.allSettled(ids.map((id) => fetchSeries(id))).then((results) => {
      const newEntries: WatchlistEntry[] = results.map((r, i) => {
        if (r.status === "fulfilled") {
          const data = r.value;
          const prices = data.prices || [];
          const latest = prices.length > 0 ? prices[prices.length - 1] : null;
          const prev = prices.length > 1 ? prices[prices.length - 2] : null;
          const change =
            latest && prev && prev.price > 0
              ? ((latest.price - prev.price) / prev.price) * 100
              : undefined;
          return {
            id: ids[i],
            name: data.title.canonical_name,
            medium: data.title.medium,
            latestPrice: latest?.price,
            priceChange: change,
            loading: false,
          };
        }
        return {
          id: ids[i],
          name: ids[i],
          medium: "—",
          loading: false,
        };
      });
      setEntries(newEntries);
      setLoading(false);
    });
  }, [ids]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold tracking-tight text-amber-400">
              HypeX
            </Link>
            <Link href="/portfolio" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
              Portfolio
            </Link>
            <span className="text-sm text-zinc-500">/</span>
            <h1 className="text-lg font-semibold">Watchlist</h1>
          </div>
          <Link
            href="/"
            className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Browse All
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
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
        ) : entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20 text-zinc-500">
            <p className="text-lg">Your watchlist is empty</p>
            <p className="text-sm">
              Click the heart icon on any title to add it here.
            </p>
            <Link
              href="/"
              className="mt-4 rounded-lg bg-amber-500 px-6 py-2 text-sm font-semibold text-zinc-900 hover:bg-amber-400 transition-colors"
            >
              Browse Titles
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-zinc-500">
              {entries.length} title{entries.length !== 1 ? "s" : ""} in watchlist
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="relative rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-amber-500/50 hover:bg-zinc-900"
                >
                  <Link href={`/series/${entry.id}`} className="block">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-zinc-100">{entry.name}</h3>
                      {entry.priceChange != null && (
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            entry.priceChange > 0
                              ? "text-emerald-400 bg-emerald-400/10"
                              : entry.priceChange < 0
                              ? "text-red-400 bg-red-400/10"
                              : "text-zinc-400 bg-zinc-800"
                          }`}
                        >
                          {entry.priceChange > 0 ? "+" : ""}
                          {entry.priceChange.toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                      <span className="rounded bg-zinc-800 px-1.5 py-0.5">{entry.medium}</span>
                      {entry.latestPrice != null && (
                        <span className="text-zinc-400">${entry.latestPrice.toFixed(0)}</span>
                      )}
                    </div>
                  </Link>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      remove(entry.id);
                    }}
                    className="absolute right-2 top-2 text-red-400/60 hover:text-red-400 transition-colors text-sm"
                    title="Remove from watchlist"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
