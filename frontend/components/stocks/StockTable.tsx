/**
 * StockTable - Generic data table for stocks, indexes, comparisons.
 * Generative UI component triggered by "showStockTable" tool.
 */

"use client";

import React from "react";
import { cn, formatPrice, formatPercent, formatNumber } from "@/lib/utils";

interface StockTableProps {
  title?: string;
  data?: {
    results?: any[];
    stocks?: any[];
    indexes?: any[];
    peers?: any[];
    data?: any[];
  };
}

export function StockTable({ title, data }: StockTableProps) {
  const rows: any[] =
    data?.results ||
    data?.stocks ||
    data?.indexes ||
    data?.peers ||
    data?.data ||
    [];

  if (!rows.length) {
    return (
      <div className="text-center py-6 text-muted-foreground">
        暂无数据
      </div>
    );
  }

  // Auto-detect columns from first row
  const firstRow = rows[0];
  const columns = Object.keys(firstRow).filter(
    (k) => !k.startsWith("_") && k !== "error"
  );

  return (
    <div className="space-y-2">
      {title && <h3 className="font-bold text-lg">{title}</h3>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left text-xs font-medium text-muted-foreground whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b last:border-0 hover:bg-muted/50 transition-colors"
              >
                {columns.map((col) => {
                  const val = row[col];
                  const formatted = formatCellValue(col, val);
                  return (
                    <td key={col} className="px-3 py-2 font-mono text-xs whitespace-nowrap">
                      {formatted}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCellValue(col: string, val: any): string {
  if (val == null) return "--";

  const colLower = col.toLowerCase();

  // Percentage columns
  if (
    colLower.includes("pct") ||
    colLower.includes("涨幅") ||
    colLower.includes("跌") ||
    colLower.includes("涨跌")
  ) {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return String(val);
    return (
      <span className={num > 0 ? "text-up" : num < 0 ? "text-down" : ""}>
        {formatPercent(num)}
      </span>
    ) as any;
  }

  // Price columns
  if (colLower.includes("price") || colLower.includes("价") || colLower.includes("open") || colLower.includes("close")) {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return String(val);
    return formatPrice(num);
  }

  // Large number columns
  if (
    colLower.includes("amount") ||
    colLower.includes("cap") ||
    colLower.includes("市值") ||
    colLower.includes("额") ||
    colLower.includes("volume") ||
    colLower.includes("量")
  ) {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return String(val);
    return formatNumber(num);
  }

  return String(val);
}
