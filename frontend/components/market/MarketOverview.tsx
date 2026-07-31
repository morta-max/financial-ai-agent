/**
 * MarketOverview - A-share market overview with key statistics.
 * Generative UI component triggered by "showMarketOverview" tool.
 */

"use client";

import React, { useEffect, useState } from "react";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import { fetchMarketOverview } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, BarChart3, DollarSign } from "lucide-react";

interface MarketOverviewProps {
  data?: any;
}

export function MarketOverview({ data: initialData }: MarketOverviewProps) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);

  useEffect(() => {
    if (initialData) return;
    fetchMarketOverview()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [initialData]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-8 w-48 rounded" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const m = data?.market || data || {};
  const topGainers = data?.top_gainers || [];
  const topLosers = data?.top_losers || [];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">📊 A股市场总览</h2>

      {/* Market stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard
          label="股票总数"
          value={m.total_stocks?.toLocaleString()}
          icon={<BarChart3 />}
        />
        <StatCard
          label="上涨"
          value={m.up_count}
          icon={<TrendingUp />}
          className="text-up bg-up-light dark:bg-red-950/20"
        />
        <StatCard
          label="下跌"
          value={m.down_count}
          icon={<TrendingDown />}
          className="text-down bg-down-light dark:bg-green-950/20"
        />
        <StatCard
          label="平盘"
          value={m.flat_count}
          icon={<Minus />}
        />
        <StatCard
          label="平均涨跌幅"
          value={formatPercent(m.avg_change_pct)}
          icon={<TrendingUp />}
          className={m.avg_change_pct > 0 ? "text-up" : m.avg_change_pct < 0 ? "text-down" : ""}
        />
        <StatCard
          label="总成交额"
          value={`${m.total_amount_billion}亿`}
          icon={<DollarSign />}
        />
        <StatCard
          label="总市值"
          value={`${m.total_mcap_trillion}万亿`}
          icon={<BarChart3 />}
        />
      </div>

      {/* Up/Down ratio bar */}
      {m.total_stocks > 0 && (
        <div className="flex h-8 rounded-full overflow-hidden">
          <div
            className="bg-up/20 flex items-center justify-end px-3 text-xs font-medium text-up transition-all"
            style={{
              width: `${(m.up_count / m.total_stocks) * 100}%`,
            }}
          >
            {((m.up_count / m.total_stocks) * 100).toFixed(0)}%
          </div>
          <div
            className="bg-muted flex items-center justify-center px-3 text-xs text-muted-foreground transition-all"
            style={{
              width: `${(m.flat_count / m.total_stocks) * 100}%`,
            }}
          >
            {((m.flat_count / m.total_stocks) * 100).toFixed(0)}%
          </div>
          <div
            className="bg-down/20 flex items-center px-3 text-xs font-medium text-down transition-all"
            style={{
              width: `${(m.down_count / m.total_stocks) * 100}%`,
            }}
          >
            {((m.down_count / m.total_stocks) * 100).toFixed(0)}%
          </div>
        </div>
      )}

      {/* Top gainers/losers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Gainers */}
        <div>
          <h3 className="font-semibold text-up mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" /> 涨幅榜 TOP 10
          </h3>
          <div className="space-y-1">
            {topGainers.map((stock: any, i: number) => (
              <div
                key={i}
                className="flex items-center justify-between px-3 py-2 rounded-lg bg-up-light dark:bg-red-950/10 text-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground w-5">{i + 1}</span>
                  <span className="font-mono font-medium">{stock.symbol}</span>
                  <span>{stock.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span>{stock.price?.toFixed(2)}</span>
                  <span className="text-up font-medium">
                    {formatPercent(stock.pct_change)}
                  </span>
                </div>
              </div>
            ))}
            {topGainers.length === 0 && (
              <div className="text-muted-foreground text-sm py-4 text-center">
                暂无数据
              </div>
            )}
          </div>
        </div>

        {/* Top Losers */}
        <div>
          <h3 className="font-semibold text-down mb-3 flex items-center gap-2">
            <TrendingDown className="w-4 h-4" /> 跌幅榜 TOP 10
          </h3>
          <div className="space-y-1">
            {topLosers.map((stock: any, i: number) => (
              <div
                key={i}
                className="flex items-center justify-between px-3 py-2 rounded-lg bg-down-light dark:bg-green-950/10 text-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground w-5">{i + 1}</span>
                  <span className="font-mono font-medium">{stock.symbol}</span>
                  <span>{stock.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span>{stock.price?.toFixed(2)}</span>
                  <span className="text-down font-medium">
                    {formatPercent(stock.pct_change)}
                  </span>
                </div>
              </div>
            ))}
            {topLosers.length === 0 && (
              <div className="text-muted-foreground text-sm py-4 text-center">
                暂无数据
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  className,
}: {
  label: string;
  value?: string | number;
  icon: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("p-4 border rounded-xl text-center", className)}>
      <div className="flex justify-center mb-1 text-muted-foreground">
        {icon}
      </div>
      <div className="text-xl font-bold">{value ?? "--"}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}
