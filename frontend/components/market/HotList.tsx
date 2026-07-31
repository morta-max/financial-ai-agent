/**
 * HotList - Displays hot stocks ranking.
 * Generative UI component triggered by "showHotList" tool.
 */

"use client";

import React, { useEffect, useState } from "react";
import { formatPercent, cn } from "@/lib/utils";
import { fetchHotStocks } from "@/lib/utils";
import { Flame } from "lucide-react";

interface HotListProps {
  data?: any;
}

export function HotList({ data: initialData }: HotListProps) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);

  useEffect(() => {
    if (initialData) return;
    fetchHotStocks()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [initialData]);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="skeleton h-6 w-32 rounded" />
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="skeleton h-10 rounded-lg" />
        ))}
      </div>
    );
  }

  const stocks = data?.stocks || data || [];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Flame className="w-5 h-5 text-orange-500" />
        <h3 className="font-bold text-lg">🔥 热门个股排行</h3>
      </div>

      {stocks.length === 0 ? (
        <div className="text-muted-foreground text-sm py-4 text-center">
          暂无热榜数据
        </div>
      ) : (
        <div className="space-y-1">
          {stocks.map((stock: any, i: number) => (
            <div
              key={i}
              className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                {/* Rank badge */}
                <span
                  className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                    i < 3
                      ? "bg-orange-500 text-white"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {stock.rank ?? stock["排名"] ?? i + 1}
                </span>
                <span className="font-mono font-medium text-sm">
                  {stock.symbol ?? stock["代码"]}
                </span>
                <span className="text-sm">{stock.name ?? stock["名称"]}</span>
              </div>
              <div className="flex items-center gap-3">
                {(stock.hot_score ?? stock["热度"]) != null && (
                  <div className="flex items-center gap-1">
                    <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-orange-500 rounded-full"
                        style={{
                          width: `${Math.min(100, (stock.hot_score ?? stock["热度"]) / 1000 * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {stock.hot_score ?? stock["热度"]}
                    </span>
                  </div>
                )}
                {stock.pct_change != null && (
                  <span
                    className={cn(
                      "text-sm font-medium",
                      stock.pct_change > 0 ? "text-up" : "text-down"
                    )}
                  >
                    {formatPercent(stock.pct_change)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="text-xs text-muted-foreground">
        共 {stocks.length} 只热门个股
      </div>
    </div>
  );
}
