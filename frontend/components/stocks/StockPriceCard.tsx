/**
 * StockPriceCard - Displays real-time stock price with key metrics.
 * Generative UI component triggered by "showStockPrice" tool.
 */

"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  cn,
  formatPrice,
  formatPercent,
  formatNumber,
  changeColor,
} from "@/lib/utils";

interface StockPriceCardProps {
  symbol?: string;
  data?: {
    symbol?: string;
    quote?: Record<string, any>;
  };
}

export function StockPriceCard({ symbol, data }: StockPriceCardProps) {
  // Extract quote from different possible data shapes
  const quote = data?.quote || data || {};
  const sym = symbol || data?.symbol || "";

  const price = quote["最新价"] || quote.price;
  const change = quote["涨跌额"] || quote.change;
  const pctChange = quote["涨跌幅(%)"] || quote.pct_change;
  const open = quote["今开"] || quote.open;
  const high = quote["最高"] || quote.high;
  const low = quote["最低"] || quote.low;
  const preClose = quote["昨收"] || quote.pre_close;
  const volume = quote["成交量(手)"] || quote.volume;
  const amount = quote["成交额(元)"] || quote.amount;
  const turnover = quote["换手率(%)"] || quote.turnover;
  const pe = quote["市盈率(TTM)"] || quote.pe_ttm;
  const pb = quote["市净率"] || quote.pb;
  const name = quote["名称"] || quote.name || "";
  const mcap = quote["总市值"] || quote.total_market_val;
  const cmcap = quote["流通市值"] || quote.circulating_market_val;

  const isUp = pctChange > 0;
  const isDown = pctChange < 0;
  const TrendIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-lg font-bold">{sym}</span>
            <span className="text-muted-foreground">{name}</span>
          </div>
        </div>
        <div
          className={cn(
            "flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium",
            isUp && "bg-up-light dark:bg-red-950/30 text-up",
            isDown && "bg-down-light dark:bg-green-950/30 text-down",
            !isUp && !isDown && "bg-muted text-muted-foreground"
          )}
        >
          <TrendIcon className="w-4 h-4" />
          <span>{formatPercent(pctChange)}</span>
        </div>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-3">
        <span className="text-4xl font-bold tracking-tight">
          {formatPrice(price)}
        </span>
        {change != null && (
          <span className={cn("text-lg", changeColor(change))}>
            {change > 0 ? "+" : ""}
            {change?.toFixed(2)}
          </span>
        )}
      </div>

      {/* Price details */}
      <div className="grid grid-cols-4 gap-3 text-sm">
        <PriceItem label="开盘" value={formatPrice(open)} />
        <PriceItem label="最高" value={formatPrice(high)} color="text-up" />
        <PriceItem label="最低" value={formatPrice(low)} color="text-down" />
        <PriceItem label="昨收" value={formatPrice(preClose)} />
      </div>

      {/* Volume & market data */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground">成交量</span>
          <p className="font-medium">{formatNumber(volume)}手</p>
        </div>
        <div>
          <span className="text-muted-foreground">成交额</span>
          <p className="font-medium">{formatNumber(amount)}</p>
        </div>
        <div>
          <span className="text-muted-foreground">换手率</span>
          <p className="font-medium">{turnover != null ? `${turnover}%` : "--"}</p>
        </div>
        <div>
          <span className="text-muted-foreground">总市值</span>
          <p className="font-medium">{formatNumber(mcap)}</p>
        </div>
      </div>

      {/* Valuation */}
      {(pe != null || pb != null) && (
        <div className="grid grid-cols-2 gap-3 pt-2 border-t text-sm">
          <div>
            <span className="text-muted-foreground">
              PE(TTM)
              {pe != null && pe < 0 && " (亏损)"}
            </span>
            <p className="font-medium">{pe != null ? pe.toFixed(2) : "--"}</p>
          </div>
          <div>
            <span className="text-muted-foreground">PB</span>
            <p className="font-medium">{pb != null ? pb.toFixed(2) : "--"}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function PriceItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <span className="text-muted-foreground">{label}</span>
      <p className={cn("font-medium", color)}>{value}</p>
    </div>
  );
}
