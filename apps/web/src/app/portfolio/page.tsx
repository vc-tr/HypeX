"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchSeries } from "@/lib/api";
import { usePortfolio, type Position, type Trade } from "@/lib/portfolio";

interface HoldingRow {
  canonical_id: string;
  name: string;
  medium: string;
  shares: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  pnl: number;
  pnl_pct: number;
}

export default function PortfolioPage() {
  const { state, sell, reset } = usePortfolio();
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showReset, setShowReset] = useState(false);

  useEffect(() => {
    if (!state.positions.length) {
      setHoldings([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    Promise.allSettled(
      state.positions.map((p) => fetchSeries(p.canonical_id))
    ).then((results) => {
      const rows: HoldingRow[] = results.map((r, i) => {
        const pos = state.positions[i];
        if (r.status === "fulfilled") {
          const prices = r.value.prices || [];
          const latest = prices.length > 0 ? prices[prices.length - 1] : null;
          const currentPrice = latest?.price ?? pos.avg_entry_price;
          const marketValue = pos.shares * currentPrice;
          const costBasis = pos.shares * pos.avg_entry_price;
          const pnl = marketValue - costBasis;
          const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
          return {
            canonical_id: pos.canonical_id,
            name: r.value.title.canonical_name,
            medium: r.value.title.medium,
            shares: pos.shares,
            avg_entry_price: pos.avg_entry_price,
            current_price: currentPrice,
            market_value: marketValue,
            pnl,
            pnl_pct: pnlPct,
          };
        }
        return {
          canonical_id: pos.canonical_id,
          name: pos.canonical_id,
          medium: "—",
          shares: pos.shares,
          avg_entry_price: pos.avg_entry_price,
          current_price: pos.avg_entry_price,
          market_value: pos.shares * pos.avg_entry_price,
          pnl: 0,
          pnl_pct: 0,
        };
      });
      setHoldings(rows);
      setLoading(false);
    });
  }, [state.positions]);

  const totalMarketValue = holdings.reduce((s, h) => s + h.market_value, 0);
  const totalPortfolioValue = state.cash + totalMarketValue;
  const totalPnl = totalPortfolioValue - 10000;
  const totalPnlPct = (totalPnl / 10000) * 100;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold tracking-tight text-amber-400">
              HypeX
            </Link>
            <Link href="/watchlist" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
              Watchlist
            </Link>
            <span className="text-sm text-zinc-500">/</span>
            <h1 className="text-lg font-semibold">Portfolio</h1>
          </div>
          <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
            Browse All
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {/* Summary Bar */}
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500">Total Value</div>
            <div className="text-xl font-bold text-amber-400">
              ${totalPortfolioValue.toFixed(2)}
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500">Available Cash</div>
            <div className="text-xl font-bold text-zinc-200">
              ${state.cash.toFixed(2)}
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500">Total P&L</div>
            <div className={`text-xl font-bold ${totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}
              <span className="ml-1 text-sm">({totalPnlPct >= 0 ? "+" : ""}{totalPnlPct.toFixed(1)}%)</span>
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-xs text-zinc-500">Positions</div>
            <div className="text-xl font-bold text-zinc-200">
              {state.positions.length}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                <div className="h-5 w-3/4 animate-pulse rounded bg-zinc-800" />
                <div className="mt-2 flex gap-2">
                  <div className="h-4 w-16 animate-pulse rounded bg-zinc-800" />
                  <div className="h-4 w-10 animate-pulse rounded bg-zinc-800" />
                </div>
              </div>
            ))}
          </div>
        ) : holdings.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20 text-zinc-500">
            <p className="text-lg">No positions yet</p>
            <p className="text-sm">Browse titles and use the Buy button to start paper trading.</p>
            <Link
              href="/"
              className="mt-4 rounded-lg bg-amber-500 px-6 py-2 text-sm font-semibold text-zinc-900 hover:bg-amber-400 transition-colors"
            >
              Browse Titles
            </Link>
          </div>
        ) : (
          <>
            {/* Holdings */}
            <div className="mb-8">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">
                Holdings
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {holdings.map((h) => (
                  <div
                    key={h.canonical_id}
                    className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-amber-500/50 hover:bg-zinc-900"
                  >
                    <Link href={`/series/${h.canonical_id}`} className="block">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-zinc-100">{h.name}</h3>
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            h.pnl >= 0
                              ? "text-emerald-400 bg-emerald-400/10"
                              : "text-red-400 bg-red-400/10"
                          }`}
                        >
                          {h.pnl >= 0 ? "+" : ""}{h.pnl_pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
                        <div>
                          <span className="text-zinc-500">Shares:</span>{" "}
                          <span className="text-zinc-300">{h.shares.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Avg Entry:</span>{" "}
                          <span className="text-zinc-300">${h.avg_entry_price.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Current:</span>{" "}
                          <span className="text-zinc-300">${h.current_price.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Value:</span>{" "}
                          <span className="text-zinc-300">${h.market_value.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                        <span className="rounded bg-zinc-800 px-1.5 py-0.5">{h.medium}</span>
                        <span className={h.pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                          P&L: {h.pnl >= 0 ? "+" : ""}${h.pnl.toFixed(2)}
                        </span>
                      </div>
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Trade History */}
        {state.trades.length > 0 && (
          <div className="mb-8">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Trade History
            </h2>
            <div className="overflow-x-auto rounded-lg border border-zinc-800">
              <table className="w-full text-sm">
                <thead className="bg-zinc-900/80 text-left text-xs text-zinc-500">
                  <tr>
                    <th className="px-4 py-2">Date</th>
                    <th className="px-4 py-2">Title</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2 text-right">Shares</th>
                    <th className="px-4 py-2 text-right">Price</th>
                    <th className="px-4 py-2 text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {state.trades.map((trade) => (
                    <tr key={trade.id} className="border-t border-zinc-800/50 hover:bg-zinc-900/30">
                      <td className="px-4 py-2 text-zinc-400">
                        {new Date(trade.timestamp).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-2">
                        <Link href={`/series/${trade.canonical_id}`} className="text-zinc-200 hover:text-amber-400">
                          {trade.canonical_id}
                        </Link>
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            trade.type === "buy"
                              ? "text-emerald-400 bg-emerald-400/10"
                              : "text-red-400 bg-red-400/10"
                          }`}
                        >
                          {trade.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-300">{trade.shares.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right text-zinc-300">${trade.price.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right text-zinc-300">${trade.total.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Reset button */}
        <div className="flex justify-center pt-4">
          {!showReset ? (
            <button
              onClick={() => setShowReset(true)}
              className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              Reset Portfolio
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500">Reset to $10,000 and clear all trades?</span>
              <button
                onClick={() => { reset(); setShowReset(false); }}
                className="rounded bg-red-500/20 px-3 py-1 text-xs text-red-400 hover:bg-red-500/30"
              >
                Confirm Reset
              </button>
              <button
                onClick={() => setShowReset(false)}
                className="text-xs text-zinc-500 hover:text-zinc-300"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
