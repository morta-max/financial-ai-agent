/**
 * KLineChart - Interactive candlestick/line chart with technical indicators.
 * Generative UI component triggered by "showKLineChart" tool.
 */

"use client";

import React, { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  ComposedChart,
  Legend,
  Area,
  AreaChart,
} from "recharts";
import { cn, formatPrice, formatPercent } from "@/lib/utils";

interface KLineChartProps {
  symbol?: string;
  data?: {
    symbol?: string;
    data?: KLineRecord[];
    count?: number;
  };
}

interface KLineRecord {
  日期?: string;
  date?: string;
  开盘?: number;
  open?: number;
  收盘?: number;
  close?: number;
  最高?: number;
  high?: number;
  最低?: number;
  low?: number;
  成交量?: number;
  volume?: number;
  成交额?: number;
  amount?: number;
  涨跌幅?: number;
  pct_change?: number;
  MA5?: number;
  MA10?: number;
  MA20?: number;
  MA60?: number;
  MACD_DIF?: number;
  MACD_DEA?: number;
  MACD_BAR?: number;
  RSI?: number;
  BOLL_UP?: number;
  BOLL_MID?: number;
  BOLL_DN?: number;
}

type IndicatorView = "price" | "volume" | "macd" | "rsi";

export function KLineChart({ symbol, data }: KLineChartProps) {
  const [indicator, setIndicator] = useState<IndicatorView>("price");
  const records: KLineRecord[] = data?.data || [];

  if (!records.length) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        暂无K线数据
      </div>
    );
  }

  const normalizedData = records.map((r) => ({
    date: (r.日期 || r.date || "").toString().slice(5), // MM-DD format
    close: r.收盘 ?? r.close ?? 0,
    open: r.开盘 ?? r.open ?? 0,
    high: r.最高 ?? r.high ?? 0,
    low: r.最低 ?? r.low ?? 0,
    volume: r.成交量 ?? r.volume ?? 0,
    amount: (r.成交额 ?? r.amount ?? 0) / 1e8, // Convert to 亿
    pct_change: r.涨跌幅 ?? r.pct_change ?? 0,
    MA5: r.MA5,
    MA10: r.MA10,
    MA20: r.MA20,
    MA60: r.MA60,
    MACD_DIF: r.MACD_DIF,
    MACD_DEA: r.MACD_DEA,
    MACD_BAR: r.MACD_BAR,
    RSI: r.RSI,
    BOLL_UP: r.BOLL_UP,
    BOLL_MID: r.BOLL_MID,
    BOLL_DN: r.BOLL_DN,
  }));

  const lastPrice = normalizedData[normalizedData.length - 1]?.close || 0;
  const prevPrice = normalizedData[normalizedData.length - 2]?.close || lastPrice;
  const priceChange = lastPrice - prevPrice;
  const isUp = priceChange >= 0;

  // Price range for Y axis
  const prices = normalizedData.flatMap((d) => [d.close, d.high, d.low].filter(Boolean));
  const priceMin = Math.min(...prices) * 0.98;
  const priceMax = Math.max(...prices) * 1.02;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;

    return (
      <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
        <p className="font-medium mb-1">{label}</p>
        <div className="space-y-0.5">
          <p>开盘: <span className="font-mono">{d.open?.toFixed(2)}</span></p>
          <p>最高: <span className="font-mono text-up">{d.high?.toFixed(2)}</span></p>
          <p>最低: <span className="font-mono text-down">{d.low?.toFixed(2)}</span></p>
          <p>收盘: <span className={cn("font-mono", d.close >= d.open ? "text-up" : "text-down")}>{d.close?.toFixed(2)}</span></p>
          <p>涨跌幅: <span className={cn(d.pct_change > 0 ? "text-up" : "text-down")}>{formatPercent(d.pct_change)}</span></p>
          <p>成交额: <span className="font-mono">{d.amount?.toFixed(2)}亿</span></p>
          {d.MA5 && <p>MA5: <span className="font-mono">{d.MA5?.toFixed(2)}</span></p>}
          {d.RSI && <p>RSI: <span className="font-mono">{d.RSI?.toFixed(1)}</span></p>}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg">
            {symbol} K线走势
          </h3>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">
              {formatPrice(lastPrice)}
            </span>
            <span className={cn("text-sm", isUp ? "text-up" : "text-down")}>
              {priceChange >= 0 ? "+" : ""}
              {priceChange.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Indicator selector */}
        <div className="flex gap-1 bg-muted rounded-lg p-1">
          {(["price", "volume", "macd", "rsi"] as IndicatorView[]).map((v) => (
            <button
              key={v}
              onClick={() => setIndicator(v)}
              className={cn(
                "px-3 py-1 text-xs rounded-md font-medium transition-colors",
                indicator === v
                  ? "bg-background shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {v === "price" ? "价格" : v === "volume" ? "成交量" : v.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          {indicator === "price" ? (
            <ComposedChart data={normalizedData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="date"
                fontSize={11}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[priceMin, priceMax]}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => v.toFixed(1)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />

              {/* Bollinger Bands */}
              {normalizedData[0]?.BOLL_UP && (
                <>
                  <Area
                    type="monotone"
                    dataKey="BOLL_UP"
                    stroke="none"
                    fill="#8884d8"
                    fillOpacity={0.05}
                    name="布林上轨"
                  />
                  <Area
                    type="monotone"
                    dataKey="BOLL_DN"
                    stroke="none"
                    fill="#8884d8"
                    fillOpacity={0.05}
                    name="布林下轨"
                  />
                  <Line
                    type="monotone"
                    dataKey="BOLL_MID"
                    stroke="#8884d8"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                    name="BOLL中轨"
                  />
                </>
              )}

              {/* Price line */}
              <Line
                type="monotone"
                dataKey="close"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="收盘价"
              />

              {/* MA lines */}
              {normalizedData[0]?.MA5 && (
                <Line
                  type="monotone"
                  dataKey="MA5"
                  stroke="#f59e0b"
                  strokeWidth={1}
                  dot={false}
                  name="MA5"
                  opacity={0.8}
                />
              )}
              {normalizedData[0]?.MA20 && (
                <Line
                  type="monotone"
                  dataKey="MA20"
                  stroke="#ef4444"
                  strokeWidth={1}
                  dot={false}
                  name="MA20"
                  opacity={0.8}
                />
              )}
              {normalizedData[0]?.MA60 && (
                <Line
                  type="monotone"
                  dataKey="MA60"
                  stroke="#8b5cf6"
                  strokeWidth={1}
                  dot={false}
                  name="MA60"
                  opacity={0.6}
                />
              )}
            </ComposedChart>
          ) : indicator === "volume" ? (
            <BarChart data={normalizedData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" fontSize={11} tickLine={false} />
              <YAxis
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${(v / 1e4).toFixed(0)}万`}
              />
              <Tooltip />
              <Bar
                dataKey="volume"
                fill={isUp ? "#ef4444" : "#22c55e"}
                opacity={0.6}
                name="成交量"
              />
            </BarChart>
          ) : indicator === "macd" ? (
            <ComposedChart data={normalizedData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" fontSize={11} tickLine={false} />
              <YAxis fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="MACD_BAR" fill="#3b82f6" opacity={0.5} name="MACD柱" />
              <Line
                type="monotone"
                dataKey="MACD_DIF"
                stroke="#ef4444"
                strokeWidth={1.5}
                dot={false}
                name="DIF"
              />
              <Line
                type="monotone"
                dataKey="MACD_DEA"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                name="DEA"
              />
            </ComposedChart>
          ) : (
            /* RSI */
            <LineChart data={normalizedData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" fontSize={11} tickLine={false} />
              <YAxis
                domain={[0, 100]}
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip />
              {/* Overbought/Oversold zones */}
              <Area
                type="monotone"
                dataKey={() => 70}
                stroke="none"
                fill="#ef4444"
                fillOpacity={0.05}
                name="超买区(70+)"
              />
              <Area
                type="monotone"
                dataKey={() => 30}
                stroke="none"
                fill="#22c55e"
                fillOpacity={0.05}
                name="超卖区(30-)"
              />
              <Line
                type="monotone"
                dataKey="RSI"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                name="RSI(14)"
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-6 gap-2 text-xs text-muted-foreground">
        {normalizedData[0]?.MA5 != null && (
          <>
            <div>
              MA5: <span className="font-mono text-foreground">{normalizedData[normalizedData.length - 1]?.MA5?.toFixed(2)}</span>
            </div>
            <div>
              MA20: <span className="font-mono text-foreground">{normalizedData[normalizedData.length - 1]?.MA20?.toFixed(2)}</span>
            </div>
            <div>
              MA60: <span className="font-mono text-foreground">{normalizedData[normalizedData.length - 1]?.MA60?.toFixed(2)}</span>
            </div>
          </>
        )}
        {normalizedData[0]?.MACD_DIF != null && (
          <div>
            MACD: <span className="font-mono text-foreground">{normalizedData[normalizedData.length - 1]?.MACD_DIF?.toFixed(3)}</span>
          </div>
        )}
        {normalizedData[0]?.RSI != null && (
          <div>
            RSI: <span className={cn("font-mono", normalizedData[normalizedData.length - 1]?.RSI > 70 ? "text-up" : normalizedData[normalizedData.length - 1]?.RSI < 30 ? "text-down" : "text-foreground")}>{normalizedData[normalizedData.length - 1]?.RSI?.toFixed(1)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
