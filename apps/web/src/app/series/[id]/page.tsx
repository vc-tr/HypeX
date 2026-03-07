"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Link from "next/link";
import { createChart, type IChartApi, CrosshairMode, AreaSeries, LineSeries, HistogramSeries } from "lightweight-charts";
import { fetchSeries, type SeriesResponse, type PricePoint, type MetricPoint } from "@/lib/api";
import { useWatchlist } from "@/lib/watchlist";
import { usePortfolio } from "@/lib/portfolio";

const RANGE_OPTIONS = [
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
  { label: "ALL", days: 0 },
];

function computeSMA(prices: { date: string; value: number }[], period: number) {
  const result: { time: string; value: number }[] = [];
  for (let i = period - 1; i < prices.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) {
      sum += prices[j].value;
    }
    result.push({ time: prices[i].date, value: sum / period });
  }
  return result;
}

export default function SeriesPage({ params }: { params: Promise<{ id: string }> }) {
  const [resolvedParams, setResolvedParams] = useState<{ id: string } | null>(null);
  const [data, setData] = useState<SeriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [rangeDays, setRangeDays] = useState(0); // 0 = ALL
  const [showSMA7, setShowSMA7] = useState(false);
  const [showSMA30, setShowSMA30] = useState(false);
  const [crosshairData, setCrosshairData] = useState<{
    price?: number;
    hype?: number;
    date?: string;
  } | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const volumeRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const volumeChartRef = useRef<IChartApi | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sma7Ref = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sma30Ref = useRef<any>(null);
  const { isIn, toggle } = useWatchlist();
  const { state: portfolio, buy, sell, getPosition } = usePortfolio();
  const [tradeMode, setTradeMode] = useState<"buy" | "sell">("buy");
  const [tradeShares, setTradeShares] = useState("");
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [tradeSuccess, setTradeSuccess] = useState<string | null>(null);

  useEffect(() => {
    params.then(setResolvedParams);
  }, [params]);

  useEffect(() => {
    if (!resolvedParams?.id) return;
    setLoading(true);
    fetchSeries(resolvedParams.id)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [resolvedParams?.id]);

  // Filter prices by date range
  const filteredPrices = useMemo(() => {
    if (!data?.prices?.length) return [];
    if (rangeDays === 0) return data.prices;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - rangeDays);
    const cutoffStr = cutoff.toISOString().split("T")[0];
    return data.prices.filter((p) => p.date >= cutoffStr);
  }, [data?.prices, rangeDays]);

  // Compute stats
  const stats = useMemo(() => {
    if (!filteredPrices.length) return null;
    const latest = filteredPrices[filteredPrices.length - 1];
    const currentPrice = latest.price;
    const currentHype = latest.hype_index;
    const allPrices = filteredPrices.map((p) => p.price);
    const ath = Math.max(...allPrices);

    // 24h change
    const prev1 = filteredPrices.length >= 2 ? filteredPrices[filteredPrices.length - 2].price : null;
    const change24h = prev1 && prev1 > 0 ? ((currentPrice - prev1) / prev1) * 100 : null;

    // 7d change
    const idx7 = filteredPrices.length - 7;
    const prev7 = idx7 >= 0 ? filteredPrices[idx7].price : null;
    const change7d = prev7 && prev7 > 0 ? ((currentPrice - prev7) / prev7) * 100 : null;

    return { currentPrice, currentHype, ath, change24h, change7d };
  }, [filteredPrices]);

  // Filter metrics for volume bars
  const mentionsData = useMemo(() => {
    if (!data?.metrics?.length) return [];
    const cutoffStr = rangeDays > 0
      ? (() => { const d = new Date(); d.setDate(d.getDate() - rangeDays); return d.toISOString().split("T")[0]; })()
      : "";
    return data.metrics
      .filter((m) => m.metric_name === "mentions_count" && (rangeDays === 0 || m.date >= cutoffStr))
      .map((m) => ({ time: m.date as string, value: m.value }));
  }, [data?.metrics, rangeDays]);

  // Main chart effect
  useEffect(() => {
    if (!chartRef.current || !filteredPrices.length) return;

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: "#18181b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      width: chartRef.current.clientWidth,
      height: 400,
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      timeScale: {
        timeVisible: false,
        secondsVisible: false,
      },
    });

    const priceData = filteredPrices.map((p) => ({
      time: p.date as string,
      value: p.price,
    }));

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#f59e0b",
      topColor: "rgba(245, 158, 11, 0.4)",
      bottomColor: "rgba(245, 158, 11, 0)",
      priceScaleId: "left",
    });
    areaSeries.setData(priceData);

    // Hype index line
    const hypeData = filteredPrices
      .filter((p) => p.hype_index != null)
      .map((p) => ({
        time: p.date as string,
        value: p.hype_index,
      }));

    if (hypeData.length > 0) {
      const hypeSeries = chart.addSeries(LineSeries, {
        color: "#8b5cf6",
        lineWidth: 2,
        priceScaleId: "right",
      });
      hypeSeries.setData(hypeData);
    }

    // SMA lines
    if (showSMA7 && priceData.length >= 7) {
      const sma7Series = chart.addSeries(LineSeries, {
        color: "#06b6d4",
        lineWidth: 1,
        lineStyle: 2, // dashed
        priceScaleId: "left",
      });
      sma7Series.setData(computeSMA(filteredPrices.map(p => ({ date: p.date, value: p.price })), 7));
      sma7Ref.current = sma7Series;
    }

    if (showSMA30 && priceData.length >= 30) {
      const sma30Series = chart.addSeries(LineSeries, {
        color: "#f472b6",
        lineWidth: 1,
        lineStyle: 2,
        priceScaleId: "left",
      });
      sma30Series.setData(computeSMA(filteredPrices.map(p => ({ date: p.date, value: p.price })), 30));
      sma30Ref.current = sma30Series;
    }

    chart.priceScale("left").applyOptions({ visible: true });
    chart.priceScale("right").applyOptions({ visible: true });
    chart.timeScale().fitContent();

    // Crosshair subscriber
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData.size) {
        setCrosshairData(null);
        return;
      }
      const priceVal = param.seriesData.get(areaSeries);
      setCrosshairData({
        price: priceVal && "value" in priceVal ? (priceVal as any).value : undefined,
        date: param.time as string,
      });
    });

    const handleResize = () => {
      if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    chartInstanceRef.current = chart;
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartInstanceRef.current = null;
      sma7Ref.current = null;
      sma30Ref.current = null;
    };
  }, [filteredPrices, showSMA7, showSMA30]);

  // Volume chart effect
  useEffect(() => {
    if (!volumeRef.current || !mentionsData.length) return;

    const chart = createChart(volumeRef.current, {
      layout: {
        background: { color: "#18181b" },
        textColor: "#a1a1aa",
      },
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      width: volumeRef.current.clientWidth,
      height: 120,
      timeScale: {
        timeVisible: false,
        secondsVisible: false,
      },
    });

    const histogramSeries = chart.addSeries(HistogramSeries, {
      color: "rgba(245, 158, 11, 0.5)",
      priceFormat: { type: "volume" },
    });
    histogramSeries.setData(mentionsData);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (volumeRef.current) chart.applyOptions({ width: volumeRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    volumeChartRef.current = chart;
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      volumeChartRef.current = null;
    };
  }, [mentionsData]);

  if (loading || !resolvedParams) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <header className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-4">
          <div className="mx-auto flex max-w-6xl items-center gap-4">
            <span className="text-amber-400">&larr; HypeX</span>
            <div className="h-6 w-48 animate-pulse rounded bg-zinc-800" />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">
          <div className="mb-4 h-4 w-64 animate-pulse rounded bg-zinc-800" />
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="mb-4 h-5 w-32 animate-pulse rounded bg-zinc-800" />
            <div className="h-[400px] w-full animate-pulse rounded bg-zinc-800/50" />
          </div>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 text-zinc-500">
        <p>Failed to load series</p>
        <Link href="/" className="text-amber-400 hover:underline">Back to titles</Link>
      </div>
    );
  }

  const isWatched = resolvedParams ? isIn(resolvedParams.id) : false;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/50 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Link href="/" className="text-amber-400 hover:underline">&larr; HypeX</Link>
          <h1 className="text-xl font-bold">{data.title.canonical_name}</h1>
          <span className="rounded bg-zinc-800 px-2 py-0.5 text-sm">{data.title.medium}</span>
          <div className="ml-auto flex items-center gap-3">
            <Link href="/watchlist" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Watchlist</Link>
            <Link href="/portfolio" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Portfolio</Link>
            <button
              onClick={() => resolvedParams && toggle(resolvedParams.id)}
              className="text-xl transition-transform hover:scale-110"
              title={isWatched ? "Remove from watchlist" : "Add to watchlist"}
            >
              {isWatched ? "❤️" : "🤍"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-4 text-sm text-zinc-500">
          {data.title.year && `Started ${data.title.year}`}
          {data.title.aliases?.length ? ` · Aliases: ${data.title.aliases.join(", ")}` : ""}
        </div>

        {/* Stats Card */}
        {stats && (
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="text-xs text-zinc-500">Price</div>
              <div className="text-lg font-bold text-amber-400">
                ${stats.currentPrice.toFixed(2)}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="text-xs text-zinc-500">Hype Index</div>
              <div className="text-lg font-bold text-violet-400">
                {stats.currentHype.toFixed(3)}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="text-xs text-zinc-500">24h Change</div>
              <div
                className={`text-lg font-bold ${
                  stats.change24h != null
                    ? stats.change24h > 0
                      ? "text-emerald-400"
                      : stats.change24h < 0
                      ? "text-red-400"
                      : "text-zinc-400"
                    : "text-zinc-600"
                }`}
              >
                {stats.change24h != null
                  ? `${stats.change24h > 0 ? "+" : ""}${stats.change24h.toFixed(2)}%`
                  : "—"}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="text-xs text-zinc-500">7d Change</div>
              <div
                className={`text-lg font-bold ${
                  stats.change7d != null
                    ? stats.change7d > 0
                      ? "text-emerald-400"
                      : stats.change7d < 0
                      ? "text-red-400"
                      : "text-zinc-400"
                    : "text-zinc-600"
                }`}
              >
                {stats.change7d != null
                  ? `${stats.change7d > 0 ? "+" : ""}${stats.change7d.toFixed(2)}%`
                  : "—"}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
              <div className="text-xs text-zinc-500">ATH</div>
              <div className="text-lg font-bold text-zinc-200">
                ${stats.ath.toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Trade Panel */}
        {stats && (() => {
          const position = resolvedParams ? getPosition(resolvedParams.id) : null;
          const currentPrice = stats.currentPrice;
          const sharesNum = parseFloat(tradeShares) || 0;
          const tradeTotal = sharesNum * currentPrice;
          const maxBuyShares = currentPrice > 0 ? Math.floor((portfolio.cash / currentPrice) * 100) / 100 : 0;
          const maxSellShares = position?.shares ?? 0;
          const unrealizedPnl = position
            ? (currentPrice - position.avg_entry_price) * position.shares
            : 0;
          const unrealizedPct = position && position.avg_entry_price > 0
            ? ((currentPrice - position.avg_entry_price) / position.avg_entry_price) * 100
            : 0;

          return (
            <div className="mb-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
              <div className="flex flex-wrap items-start gap-6">
                {/* Position info */}
                {position && (
                  <div className="flex-1 min-w-[200px]">
                    <div className="text-xs text-zinc-500 mb-2">Your Position</div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-zinc-500">Shares:</span>{" "}
                        <span className="text-zinc-200">{position.shares.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Avg Entry:</span>{" "}
                        <span className="text-zinc-200">${position.avg_entry_price.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Value:</span>{" "}
                        <span className="text-zinc-200">${(position.shares * currentPrice).toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500">P&L:</span>{" "}
                        <span className={unrealizedPnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                          {unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)} ({unrealizedPct >= 0 ? "+" : ""}{unrealizedPct.toFixed(1)}%)
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Trade form */}
                <div className="flex-1 min-w-[280px]">
                  <div className="flex items-center gap-2 mb-3">
                    <button
                      onClick={() => { setTradeMode("buy"); setTradeError(null); setTradeSuccess(null); }}
                      className={`rounded px-4 py-1.5 text-sm font-medium transition-colors ${
                        tradeMode === "buy"
                          ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/50"
                          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                      }`}
                    >
                      Buy
                    </button>
                    <button
                      onClick={() => { setTradeMode("sell"); setTradeError(null); setTradeSuccess(null); }}
                      className={`rounded px-4 py-1.5 text-sm font-medium transition-colors ${
                        tradeMode === "sell"
                          ? "bg-red-500/20 text-red-400 ring-1 ring-red-500/50"
                          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                      }`}
                    >
                      Sell
                    </button>
                    <span className="ml-auto text-xs text-zinc-500">
                      Cash: ${portfolio.cash.toFixed(2)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="Shares"
                      value={tradeShares}
                      onChange={(e) => {
                        setTradeShares(e.target.value);
                        setTradeError(null);
                        setTradeSuccess(null);
                      }}
                      className="w-28 rounded border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
                    />
                    <button
                      onClick={() => {
                        const max = tradeMode === "buy" ? maxBuyShares : maxSellShares;
                        setTradeShares(max.toFixed(2));
                      }}
                      className="rounded bg-zinc-800 px-2 py-1.5 text-xs text-zinc-400 hover:bg-zinc-700"
                    >
                      Max
                    </button>
                    <span className="text-sm text-zinc-500">
                      @ ${currentPrice.toFixed(2)} = <span className="text-zinc-300">${tradeTotal.toFixed(2)}</span>
                    </span>
                  </div>

                  {tradeError && (
                    <div className="mt-2 text-xs text-red-400">{tradeError}</div>
                  )}
                  {tradeSuccess && (
                    <div className="mt-2 text-xs text-emerald-400">{tradeSuccess}</div>
                  )}

                  <button
                    onClick={() => {
                      if (!resolvedParams || sharesNum <= 0) {
                        setTradeError("Enter a valid number of shares");
                        return;
                      }
                      const err = tradeMode === "buy"
                        ? buy(resolvedParams.id, sharesNum, currentPrice)
                        : sell(resolvedParams.id, sharesNum, currentPrice);
                      if (err) {
                        setTradeError(err);
                      } else {
                        setTradeSuccess(
                          `${tradeMode === "buy" ? "Bought" : "Sold"} ${sharesNum.toFixed(2)} shares at $${currentPrice.toFixed(2)}`
                        );
                        setTradeShares("");
                      }
                    }}
                    className={`mt-3 w-full rounded py-2 text-sm font-semibold transition-colors ${
                      tradeMode === "buy"
                        ? "bg-emerald-500 text-zinc-900 hover:bg-emerald-400"
                        : "bg-red-500 text-white hover:bg-red-400"
                    }`}
                  >
                    {tradeMode === "buy" ? "Buy" : "Sell"} {sharesNum > 0 ? `${sharesNum.toFixed(2)} shares` : ""}
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Chart */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">Price &amp; Hype Index</h2>
              {/* Crosshair tooltip */}
              {crosshairData && (
                <span className="text-xs text-zinc-400">
                  {crosshairData.date} — ${crosshairData.price?.toFixed(2) ?? "—"}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Date range buttons */}
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => setRangeDays(opt.days)}
                  className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                    rangeDays === opt.days
                      ? "bg-amber-500 text-zinc-900"
                      : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
              {/* SMA toggles */}
              <button
                onClick={() => setShowSMA7((v) => !v)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  showSMA7
                    ? "bg-cyan-500/20 text-cyan-400 ring-1 ring-cyan-500/50"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
              >
                7 SMA
              </button>
              <button
                onClick={() => setShowSMA30((v) => !v)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  showSMA30
                    ? "bg-pink-500/20 text-pink-400 ring-1 ring-pink-500/50"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
              >
                30 SMA
              </button>
            </div>
          </div>

          {/* Legend */}
          <div className="mb-2 flex items-center gap-4 text-xs text-zinc-400">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-4 rounded-sm bg-amber-500" />
              Price
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-violet-500" />
              Hype Index
            </span>
            {showSMA7 && (
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-4 bg-cyan-500" style={{ borderTop: "1px dashed" }} />
                7 SMA
              </span>
            )}
            {showSMA30 && (
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-4 bg-pink-500" style={{ borderTop: "1px dashed" }} />
                30 SMA
              </span>
            )}
          </div>

          <div ref={chartRef} className="w-full" />

          {/* Volume bars */}
          {mentionsData.length > 0 && (
            <div className="mt-2">
              <div className="mb-1 text-xs text-zinc-500">Mentions Volume</div>
              <div ref={volumeRef} className="w-full" />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
