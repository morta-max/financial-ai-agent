/**
 * RiskGauge - Displays investment risk and return metrics.
 * Generative UI component triggered by "showRiskAnalysis" tool.
 */

"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Shield, TrendingUp, TrendingDown, BarChart3, Target } from "lucide-react";

interface RiskGaugeProps {
  symbol?: string;
  data?: Record<string, any>;
}

export function RiskGauge({ symbol, data }: RiskGaugeProps) {
  const d = data || {};

  if (d.error) {
    return (
      <div className="text-destructive text-sm">{d.error}</div>
    );
  }

  const sym = symbol || d["股票代码"] || "";
  const name = d["股票名称"] || "";
  const riskLevel = d["风险等级"] || "--";
  const score = d["综合评分"] || 0;
  const period = d["分析周期"] || "";

  const returns = d["收益指标"] || {};
  const risk = d["风险指标"] || {};
  const riskAdj = d["风险调整收益"] || {};
  const benchmark = d["基准对比"] || {};
  const latestPrice = d["最新价格"];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-lg">
            {sym} {name}
          </h3>
          <p className="text-sm text-muted-foreground">风险与回报分析 · {period}</p>
        </div>
        <div className="text-right">
          <div
            className={cn(
              "inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium",
              riskLevel.includes("低") && "bg-down-light dark:bg-green-950/30 text-down",
              riskLevel.includes("中等") && "bg-yellow-100 dark:bg-yellow-950/30 text-yellow-600",
              riskLevel.includes("高") && "bg-up-light dark:bg-red-950/30 text-up",
            )}
          >
            <Shield className="w-4 h-4" />
            {riskLevel}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            最新价: ¥{latestPrice?.toFixed(2) || "--"}
          </div>
        </div>
      </div>

      {/* Score gauge */}
      <div className="flex items-center justify-center py-4">
        <ScoreGauge score={score} />
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricBox
          label="年化收益率"
          value={`${returns["年化收益率(%)"] ?? "--"}%`}
          icon={<TrendingUp className="w-4 h-4" />}
          positive={returns["年化收益率(%)"] > 0}
        />
        <MetricBox
          label="年化波动率"
          value={`${risk["年化波动率(%)"] ?? "--"}%`}
          icon={<BarChart3 className="w-4 h-4" />}
          positive={risk["年化波动率(%)"] < 30}
        />
        <MetricBox
          label="夏普比率"
          value={riskAdj["夏普比率"]?.toFixed(2) ?? "--"}
          icon={<Target className="w-4 h-4" />}
          positive={(riskAdj["夏普比率"] ?? 0) > 0.5}
        />
        <MetricBox
          label="最大回撤"
          value={`${risk["最大回撤"]?.max_drawdown_pct ?? "--"}%`}
          icon={<TrendingDown className="w-4 h-4" />}
          positive={(risk["最大回撤"]?.max_drawdown ?? -1) > -0.2}
          danger
        />
      </div>

      {/* Detailed metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Returns section */}
        <div className="p-3 border rounded-lg">
          <h4 className="text-sm font-semibold mb-2">收益分析</h4>
          <div className="space-y-1 text-sm">
            <Row label="累计收益率" value={`${returns["累计收益率(%)"]}%`} />
            <Row label="胜率" value={`${returns["胜率"]?.win_rate}%`} />
            <Row label="盈亏比" value={returns["胜率"]?.profit_factor?.toFixed(2)} />
            <Row label="最佳日" value={`${returns["最佳日收益(%)"]}%`} color="text-up" />
            <Row label="最差日" value={`${returns["最差日收益(%)"]}%`} color="text-down" />
          </div>
        </div>

        {/* Risk section */}
        <div className="p-3 border rounded-lg">
          <h4 className="text-sm font-semibold mb-2">风险指标</h4>
          <div className="space-y-1 text-sm">
            <Row label="VaR(95%)" value={`${risk["VaR/CVaR"]?.VaR_95}%`} />
            <Row label="CVaR(95%)" value={`${risk["VaR/CVaR"]?.CVaR_95}%`} />
            <Row label="索提诺比率" value={riskAdj["索提诺比率"]?.toFixed(3)} />
            <Row label="卡玛比率" value={riskAdj["卡玛比率"]?.toFixed(3)} />
            <Row label="信息比率" value={riskAdj["信息比率"]?.toFixed(3)} />
          </div>
        </div>

        {/* Benchmark section */}
        <div className="p-3 border rounded-lg">
          <h4 className="text-sm font-semibold mb-2">基准对比</h4>
          <div className="space-y-1 text-sm">
            <Row label="Beta" value={benchmark["Beta"]?.toFixed(3)} />
            <Row label="Alpha" value={`${benchmark["Alpha(%)"]}%`} />
            <Row label="R²" value={benchmark["R²"]?.toFixed(3)} />
            <Row label="相关性" value={benchmark["相关性"]?.toFixed(3)} />
            <Row label="上涨/下跌" value={`${risk["上涨天数"]}/${risk["下跌天数"]}`} />
          </div>
        </div>
      </div>

      {/* Drawdown info */}
      {risk["最大回撤"] && (
        <div className="p-3 bg-muted/50 rounded-lg text-sm">
          <span className="text-muted-foreground">最大回撤详情: </span>
          {risk["最大回撤"].max_drawdown_pct}% |
          峰值日: {risk["最大回撤"].peak_date || "--"} |
          谷底日: {risk["最大回撤"].trough_date || "--"}
          {risk["最大回撤"].recovery_date && (
            <> | 恢复日: {risk["最大回撤"].recovery_date}</>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreGauge({ score }: { score: number }) {
  const angle = (score / 100) * 180 - 90; // -90 to 90 degrees
  const color =
    score >= 70 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative w-40 h-20 overflow-hidden">
      {/* Semi-circle background */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-40 h-20 rounded-t-full border-[12px] border-muted border-b-0" />
      {/* Score arc */}
      <svg
        className="absolute bottom-0 left-1/2 -translate-x-1/2"
        width="160"
        height="80"
        viewBox="0 0 160 80"
      >
        <path
          d={`M 10 70 A 70 70 0 0 1 150 70`}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={`${(score / 100) * 220} 220`}
          strokeLinecap="round"
        />
      </svg>
      {/* Score text */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-center">
        <div className="text-2xl font-bold">{score}</div>
        <div className="text-[10px] text-muted-foreground">/100</div>
      </div>
    </div>
  );
}

function MetricBox({
  label,
  value,
  icon,
  positive,
  danger,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  positive?: boolean;
  danger?: boolean;
}) {
  return (
    <div className="p-3 border rounded-lg text-center">
      <div className="flex justify-center mb-1 text-muted-foreground">{icon}</div>
      <div
        className={cn(
          "text-lg font-bold",
          positive === true && !danger && "text-down",
          positive === false && !danger && "text-up",
          danger && positive === true && "text-down",
          danger && positive === false && "text-up"
        )}
      >
        {value}
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function Row({
  label,
  value,
  color,
}: {
  label: string;
  value?: string | null;
  color?: string;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-mono font-medium", color)}>{value ?? "--"}</span>
    </div>
  );
}
