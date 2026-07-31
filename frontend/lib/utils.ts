/**
 * Utility functions for the Financial AI Agent frontend.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind CSS classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format large numbers with Chinese units */
export function formatNumber(num: number | null | undefined): string {
  if (num == null) return "--";
  if (Math.abs(num) >= 1e12) return (num / 1e12).toFixed(2) + "万亿";
  if (Math.abs(num) >= 1e8) return (num / 1e8).toFixed(2) + "亿";
  if (Math.abs(num) >= 1e4) return (num / 1e4).toFixed(2) + "万";
  return num.toLocaleString("zh-CN");
}

/** Format price with appropriate decimals */
export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "--";
  if (price >= 100) return price.toFixed(2);
  if (price >= 10) return price.toFixed(2);
  return price.toFixed(2);
}

/** Format percentage change */
export function formatPercent(pct: number | null | undefined): string {
  if (pct == null) return "--";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

/** Format date string */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "--";
  // Handle YYYYMMDD
  if (dateStr.length === 8) {
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
  }
  // Handle YYYY-MM-DD
  if (dateStr.includes("-")) return dateStr;
  return dateStr;
}

/** Determine up/down color class */
export function changeColor(val: number | null | undefined): string {
  if (val == null) return "";
  if (val > 0) return "text-up";
  if (val < 0) return "text-down";
  return "text-muted-foreground";
}

/** Determine background color for up/down */
export function changeBg(val: number | null | undefined): string {
  if (val == null) return "";
  if (val > 0) return "bg-up-light dark:bg-red-950/30";
  if (val < 0) return "bg-down-light dark:bg-green-950/30";
  return "";
}

/** API base URL */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Fetch helper */
export async function apiFetch<T = any>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

/** Fetch stock quote */
export async function fetchStockQuote(symbol: string) {
  return apiFetch(`/api/stocks/${symbol}/quote`);
}

/** Fetch stock K-line */
export async function fetchStockKline(
  symbol: string,
  period = "daily",
  limit = 60,
  withIndicators = true
) {
  return apiFetch(
    `/api/stocks/${symbol}/kline?period=${period}&limit=${limit}&with_indicators=${withIndicators}`
  );
}

/** Fetch stock financials */
export async function fetchStockFinancials(symbol: string) {
  return apiFetch(`/api/stocks/${symbol}/financials`);
}

/** Fetch stock valuation */
export async function fetchStockValuation(symbol: string) {
  return apiFetch(`/api/stocks/${symbol}/valuation`);
}

/** Fetch stock risk analysis */
export async function fetchStockRisk(symbol: string, days = 252) {
  return apiFetch(`/api/stocks/${symbol}/risk?days=${days}`);
}

/** Search stocks */
export async function searchStocks(query: string, limit = 20) {
  return apiFetch(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

/** Get market overview */
export async function fetchMarketOverview() {
  return apiFetch("/api/market/overview");
}

/** Get indexes */
export async function fetchIndexes() {
  return apiFetch("/api/market/indexes");
}

/** Get limit-up pool */
export async function fetchLimitUp(date?: string) {
  const params = date ? `?date=${date}` : "";
  return apiFetch(`/api/market/limit-up${params}`);
}

/** Get hot stocks */
export async function fetchHotStocks() {
  return apiFetch("/api/market/hot-stocks");
}

/** Get peer comparison */
export async function fetchPeers(symbol: string) {
  return apiFetch(`/api/stocks/${symbol}/peers`);
}
