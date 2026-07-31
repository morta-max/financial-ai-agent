/**
 * ValuationCard - Displays PE/PB/PS/PCF valuation analysis.
 * Generative UI component triggered by "showValuation" tool.
 */

"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ValuationCardProps {
  symbol?: string;
  data?: Record<string, any>;
}

export function ValuationCard({ symbol, data }: ValuationCardProps) {
  const d = data || {};

  if (d.error) {
    return (
      <div className="text-destructive text-sm">{d.error}</div>
    );
  }

  const sym = symbol || d["股票代码"] || "";
  const name = d["股票名称"] || "";
  const currentPrice = d["当前价格"];
  const score = d.valuation_score;
  const rating = d.valuation_rating;
  const summary = d.valuation_summary;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg">
            {sym} {name}
          </h3>
          <p className="text-sm text-muted-foreground">估值分析</p>
        </div>
        {score != null && (
          <div
            className={cn(
              "px-4 py-2 rounded-xl text-center",
              score >= 65
                ? "bg-down-light dark:bg-green-950/30"
                : score >= 45
                ? "bg-muted"
                : "bg-up-light dark:bg-red-950/30"
            )}
          >
            <div className="text-2xl font-bold">{score}</div>
            <div className="text-xs text-muted-foreground">综合评分</div>
          </div>
        )}
      </div>

      {/* Rating */}
      {rating && (
        <div className="text-center py-2 bg-muted rounded-lg">
          <span className="text-lg font-bold">{rating}</span>
        </div>
      )}

      {/* PE/PB/PS/PCF grid */}
      <div className="grid grid-cols-2 gap-3">
        <ValuationItem
          label="PE (TTM)"
          value={d.pe_ttm}
          percentile={d.pe_percentile}
          zone={d.pe_zone}
          median={d.pe_median}
          low25={d.pe_25pct}
          high75={d.pe_75pct}
        />
        <ValuationItem
          label="PB"
          value={d.pb}
          percentile={d.pb_percentile}
          zone={d.pb_zone}
          median={d.pb_median}
          low25={d.pb_25pct}
          high75={d.pb_75pct}
        />
        <ValuationItem
          label="PS (TTM)"
          value={d.ps_ttm}
          percentile={d.ps_percentile}
          avg={d.ps_avg}
        />
        <ValuationItem
          label="PCF"
          value={d.pcf}
          percentile={d.pcf_percentile}
        />
      </div>

      {/* Summary */}
      {summary && (
        <div className="text-sm text-muted-foreground p-3 bg-muted/50 rounded-lg">
          💡 {summary}
        </div>
      )}

      {currentPrice && (
        <div className="text-xs text-muted-foreground">
          当前价格: ¥{currentPrice} | 数据更新时间: {d["分析时间"] || "--"}
        </div>
      )}
    </div>
  );
}

function ValuationItem({
  label,
  value,
  percentile,
  zone,
  median,
  avg,
  low25,
  high75,
}: {
  label: string;
  value?: number | null;
  percentile?: number | null;
  zone?: string;
  median?: number | null;
  avg?: number | null;
  low25?: number | null;
  high75?: number | null;
}) {
  if (value == null && zone == null) return null;

  const isLow = percentile != null && percentile < 25;
  const isHigh = percentile != null && percentile > 75;

  return (
    <div className="p-3 border rounded-lg">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold">
        {value != null ? value.toFixed(2) : "--"}
      </div>
      {percentile != null && (
        <div className="flex items-center gap-2 mt-1">
          {/* Percentile bar */}
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                isLow
                  ? "bg-down"
                  : isHigh
                  ? "bg-up"
                  : "bg-primary"
              )}
              style={{ width: `${Math.min(100, Math.max(0, percentile))}%` }}
            />
          </div>
          <span
            className={cn(
              "text-xs font-medium",
              isLow ? "text-down" : isHigh ? "text-up" : "text-muted-foreground"
            )}
          >
            分位 {percentile.toFixed(0)}%
          </span>
        </div>
      )}
      {median != null && (
        <div className="text-xs text-muted-foreground mt-1">
          中位: {median.toFixed(2)} | 25%: {low25?.toFixed(2)} | 75%: {high75?.toFixed(2)}
        </div>
      )}
      {avg != null && (
        <div className="text-xs text-muted-foreground mt-1">
          均值: {avg.toFixed(2)}
        </div>
      )}
      {zone && (
        <div
          className={cn(
            "text-xs mt-1 font-medium",
            isLow ? "text-down" : isHigh ? "text-up" : "text-muted-foreground"
          )}
        >
          {zone}
        </div>
      )}
    </div>
  );
}
