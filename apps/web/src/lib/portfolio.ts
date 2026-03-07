"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "hypex-portfolio";
const INITIAL_CASH = 10000;
const MIN_SHARES = 0.01;

export interface Position {
  canonical_id: string;
  shares: number;
  avg_entry_price: number;
  first_bought: string;
}

export interface Trade {
  id: string;
  canonical_id: string;
  type: "buy" | "sell";
  shares: number;
  price: number;
  total: number;
  timestamp: string;
}

export interface PortfolioState {
  cash: number;
  positions: Position[];
  trades: Trade[];
}

const INITIAL_STATE: PortfolioState = {
  cash: INITIAL_CASH,
  positions: [],
  trades: [],
};

function getStoredPortfolio(): PortfolioState {
  if (typeof window === "undefined") return INITIAL_STATE;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return INITIAL_STATE;
    const parsed = JSON.parse(raw);
    return {
      cash: parsed.cash ?? INITIAL_CASH,
      positions: parsed.positions ?? [],
      trades: parsed.trades ?? [],
    };
  } catch {
    return INITIAL_STATE;
  }
}

function setStoredPortfolio(state: PortfolioState) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function usePortfolio() {
  const [state, setState] = useState<PortfolioState>(INITIAL_STATE);

  useEffect(() => {
    setState(getStoredPortfolio());
  }, []);

  const persist = useCallback((next: PortfolioState) => {
    setState(next);
    setStoredPortfolio(next);
  }, []);

  const buy = useCallback(
    (canonical_id: string, shares: number, currentPrice: number): string | null => {
      if (shares < MIN_SHARES) return "Minimum trade is 0.01 shares";
      const total = shares * currentPrice;
      if (total > state.cash) return "Insufficient cash";

      const existing = state.positions.find((p) => p.canonical_id === canonical_id);
      let nextPositions: Position[];
      if (existing) {
        const totalShares = existing.shares + shares;
        const totalCost = existing.shares * existing.avg_entry_price + total;
        nextPositions = state.positions.map((p) =>
          p.canonical_id === canonical_id
            ? { ...p, shares: totalShares, avg_entry_price: totalCost / totalShares }
            : p
        );
      } else {
        nextPositions = [
          ...state.positions,
          {
            canonical_id,
            shares,
            avg_entry_price: currentPrice,
            first_bought: new Date().toISOString().split("T")[0],
          },
        ];
      }

      const trade: Trade = {
        id: crypto.randomUUID(),
        canonical_id,
        type: "buy",
        shares,
        price: currentPrice,
        total,
        timestamp: new Date().toISOString(),
      };

      persist({
        cash: state.cash - total,
        positions: nextPositions,
        trades: [trade, ...state.trades],
      });
      return null;
    },
    [state, persist]
  );

  const sell = useCallback(
    (canonical_id: string, shares: number, currentPrice: number): string | null => {
      if (shares < MIN_SHARES) return "Minimum trade is 0.01 shares";
      const existing = state.positions.find((p) => p.canonical_id === canonical_id);
      if (!existing) return "No position to sell";
      if (shares > existing.shares + 0.001) return "Cannot sell more shares than held";

      const actualShares = Math.min(shares, existing.shares);
      const total = actualShares * currentPrice;

      let nextPositions: Position[];
      if (Math.abs(existing.shares - actualShares) < MIN_SHARES) {
        nextPositions = state.positions.filter((p) => p.canonical_id !== canonical_id);
      } else {
        nextPositions = state.positions.map((p) =>
          p.canonical_id === canonical_id
            ? { ...p, shares: p.shares - actualShares }
            : p
        );
      }

      const trade: Trade = {
        id: crypto.randomUUID(),
        canonical_id,
        type: "sell",
        shares: actualShares,
        price: currentPrice,
        total,
        timestamp: new Date().toISOString(),
      };

      persist({
        cash: state.cash + total,
        positions: nextPositions,
        trades: [trade, ...state.trades],
      });
      return null;
    },
    [state, persist]
  );

  const getPosition = useCallback(
    (canonical_id: string): Position | null => {
      return state.positions.find((p) => p.canonical_id === canonical_id) ?? null;
    },
    [state.positions]
  );

  const reset = useCallback(() => {
    persist(INITIAL_STATE);
  }, [persist]);

  const totalValue = useCallback(
    (priceMap: Record<string, number>): number => {
      const positionsValue = state.positions.reduce((sum, p) => {
        const price = priceMap[p.canonical_id] ?? p.avg_entry_price;
        return sum + p.shares * price;
      }, 0);
      return state.cash + positionsValue;
    },
    [state]
  );

  return { state, buy, sell, getPosition, reset, totalValue };
}
