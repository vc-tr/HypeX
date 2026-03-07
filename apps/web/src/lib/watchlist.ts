"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "hypex-watchlist";

function getStoredWatchlist(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function setStoredWatchlist(ids: string[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

/**
 * React hook for managing a localStorage-backed watchlist of title IDs.
 */
export function useWatchlist() {
  const [ids, setIds] = useState<string[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    setIds(getStoredWatchlist());
  }, []);

  const add = useCallback((id: string) => {
    setIds((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id];
      setStoredWatchlist(next);
      return next;
    });
  }, []);

  const remove = useCallback((id: string) => {
    setIds((prev) => {
      const next = prev.filter((x) => x !== id);
      setStoredWatchlist(next);
      return next;
    });
  }, []);

  const toggle = useCallback((id: string) => {
    setIds((prev) => {
      const next = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id];
      setStoredWatchlist(next);
      return next;
    });
  }, []);

  const isIn = useCallback(
    (id: string) => ids.includes(id),
    [ids]
  );

  const getAll = useCallback(() => ids, [ids]);

  return { ids, add, remove, toggle, isIn, getAll };
}
