/**
 * LimitUpPool - Displays today's limit-up stocks.
 * Generative UI component triggered by "showLimitUpPool" tool.
 */

"use client";

import React, { useEffect, useState } from "react";
import { formatNumber, formatPercent, cn } from "@/lib/utils";
import { fetchLimitUp } from "@/lib/utils";
import { Rocket, ArrowUp } from "lucide-react";

interface LimitUpPoolProps {
  data?: any;
}

export function LimitUpPool({ data: initialData }: LimitUpPoolProps) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);

  useEffect(() => {
    if (initialData) return;
    fetchLimitUp()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [initialData]);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="skeleton h-6 w-32 rounded" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-12 rounded-lg" />
        ))}
      </div>
    );
  }

  const stocks = data?.stocks || data || [];
  const date = data?.date || "";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Rocket className="w-5 h-5 text-up" />
        <h3 className="font-bold text-lg">🚀 涨停池</h3>
        {date && (
          <span className="text-xs text-muted-foreground ml-2">{date}</span>
        )}
      </div>

      {stocks.length === 0 ? (
        <div className="text-muted-foreground text-sm py-4 text-center">
          今日暂无涨停数据或非交易日
        </div>
      ) : (
        <div className="space-y-1">
          {stocks.map((stock: any, i: number) => (
            <div
              key={i}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-up-light dark:bg-red-950/10 hover:bg-up-light/80 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-5">
                  {i + 1}
                </span>
                <span className="font-mono font-medium text-sm">
                  {stock.symbol}
                </span>
                <span className="text-sm">{stock.name}</span>
                {(stock.limit_times ?? stock["连板数"]) > 1 && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-up/10 text-up font-bold">
                    {(stock.limit_times ?? stock["连板数"])}连板
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-up font-medium">
                  {formatPercent(stock.pct_change ?? stock["涨跌幅(%)"])}
                </span>
                {stock.turnover != null && (
                  <span className="text-muted-foreground text-xs">
                    换手 {stock.turnover}%
                  </span>
                )}
                {(stock.limit_funds ?? stock["封单资金"]) != null && (
                  <span className="text-muted-foreground text-xs">
                    封单 {formatNumber(stock.limit_funds ?? stock["封单资金"])}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="text-xs text-muted-foreground">
        涨停数量: {stocks.length} 只
      </div>
    </div>
  );
}
