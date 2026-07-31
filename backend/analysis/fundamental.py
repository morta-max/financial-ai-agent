"""
Fundamental analysis module.
Scores companies based on profitability, growth, solvency, and efficiency.
"""

import numpy as np
import pandas as pd
from typing import Optional


class FundamentalAnalyzer:
    """Analyzer for company fundamental health."""

    async def analyze(self, symbol: str, client) -> dict:
        """
        Generate a fundamental score and summary for a stock.

        Args:
            symbol: Stock code
            client: AKShareClient instance

        Returns:
            Dictionary with fundamental scores and analysis
        """
        try:
            # Fetch financial indicators
            indicators_df = await client.get_financial_indicators(symbol)

            if indicators_df is None or indicators_df.empty:
                return {"error": f"无法获取 {symbol} 的财务指标数据"}

            # Calculate scores from latest data
            scores = self._score_financials(indicators_df)
            summary = self._generate_summary(scores, indicators_df)

            return {
                "股票代码": symbol,
                "财务评分": scores["total_score"],
                "评级": scores["rating"],
                "各维度评分": {
                    "盈利能力": scores["profitability"],
                    "成长能力": scores["growth"],
                    "偿债能力": scores["solvency"],
                    "运营效率": scores["efficiency"],
                },
                "核心指标": scores["key_metrics"],
                "分析摘要": summary,
            }

        except Exception as e:
            return {"error": f"基本面分析失败: {str(e)}"}

    def _score_financials(self, df: pd.DataFrame) -> dict:
        """Score financial indicators on a 0-100 scale."""
        if df.empty:
            return {"total_score": 0, "rating": "数据不足"}

        latest = df.iloc[0]

        profitability = self._score_profitability(latest)
        growth = self._score_growth(df)
        solvency = self._score_solvency(latest)
        efficiency = self._score_efficiency(latest)

        total = (profitability * 0.35 + growth * 0.25 +
                 solvency * 0.25 + efficiency * 0.15)

        if total >= 85:
            rating = "优秀 ⭐⭐⭐⭐⭐"
        elif total >= 70:
            rating = "良好 ⭐⭐⭐⭐"
        elif total >= 55:
            rating = "一般 ⭐⭐⭐"
        elif total >= 40:
            rating = "较差 ⭐⭐"
        else:
            rating = "差 ⭐"

        return {
            "total_score": round(total, 1),
            "rating": rating,
            "profitability": round(profitability, 1),
            "growth": round(growth, 1),
            "solvency": round(solvency, 1),
            "efficiency": round(efficiency, 1),
            "key_metrics": self._extract_key_metrics(df),
        }

    def _score_profitability(self, row: pd.Series) -> float:
        """Score profitability (0-100)."""
        score = 50

        # ROE (权重最大的盈利指标)
        roe = self._safe_float(row, 'roe')
        if roe is not None:
            if roe > 20:
                score += 30
            elif roe > 15:
                score += 20
            elif roe > 10:
                score += 10
            elif roe > 5:
                score += 0
            elif roe > 0:
                score -= 10
            else:
                score -= 20

        # Gross margin
        gross = self._safe_float(row, 'grossprofit_margin') or self._safe_float(row, 'gross_margin')
        if gross is not None:
            if gross > 60:
                score += 15
            elif gross > 40:
                score += 10
            elif gross > 20:
                score += 5
            elif gross < 10:
                score -= 10

        # Net margin
        net = self._safe_float(row, 'netprofit_margin') or self._safe_float(row, 'net_margin')
        if net is not None:
            if net > 20:
                score += 15
            elif net > 10:
                score += 10
            elif net > 5:
                score += 5
            elif net < 0:
                score -= 15

        return max(0, min(100, score))

    def _score_growth(self, df: pd.DataFrame) -> float:
        """Score growth trajectory (0-100)."""
        score = 50
        if len(df) < 2:
            return score

        latest = df.iloc[0]
        prev = df.iloc[min(1, len(df) - 1)]

        # Revenue growth
        rev_key = 'or_yoy' if 'or_yoy' in df.columns else None
        if rev_key is None:
            rev_key = 'total_revenue' if 'total_revenue' in df.columns else None

        if rev_key:
            rev_latest = self._safe_float(latest, rev_key)
            rev_prev = self._safe_float(prev, rev_key)
            if rev_latest and rev_prev and rev_prev != 0:
                rev_growth = (rev_latest - rev_prev) / abs(rev_prev) * 100
                if rev_growth > 30:
                    score += 20
                elif rev_growth > 15:
                    score += 12
                elif rev_growth > 5:
                    score += 5
                elif rev_growth < -10:
                    score -= 15

        # Net profit growth
        profit_key = 'netprofit_yoy' if 'netprofit_yoy' in df.columns else None
        if profit_key is None:
            profit_key = 'net_profit_parent' if 'net_profit_parent' in df.columns else None

        if profit_key:
            p_latest = self._safe_float(latest, profit_key)
            p_prev = self._safe_float(prev, profit_key)
            if p_latest and p_prev and p_prev != 0:
                profit_growth = (p_latest - p_prev) / abs(p_prev) * 100
                if profit_growth > 30:
                    score += 20
                elif profit_growth > 15:
                    score += 12
                elif profit_growth > 5:
                    score += 5
                elif profit_growth < -20:
                    score -= 20

        return max(0, min(100, score))

    def _score_solvency(self, row: pd.Series) -> float:
        """Score solvency/debt health (0-100)."""
        score = 50

        # Debt ratio
        debt = self._safe_float(row, 'debt_to_assets') or self._safe_float(row, 'debt_ratio')
        if debt is not None:
            if debt < 30:
                score += 20
            elif debt < 50:
                score += 10
            elif debt < 70:
                score += 0
            elif debt < 85:
                score -= 10
            else:
                score -= 20

        # Current ratio
        current = self._safe_float(row, 'current_ratio')
        if current is not None:
            if 1.5 <= current <= 3:
                score += 15
            elif 1 <= current < 1.5 or 3 < current <= 5:
                score += 5
            elif current < 0.8:
                score -= 15

        # Quick ratio
        quick = self._safe_float(row, 'quick_ratio')
        if quick is not None:
            if 0.8 <= quick <= 2:
                score += 15
            elif quick < 0.5:
                score -= 10

        return max(0, min(100, score))

    def _score_efficiency(self, row: pd.Series) -> float:
        """Score operational efficiency (0-100)."""
        score = 50

        # Asset turnover
        turnover = self._safe_float(row, 'asset_turnover')
        if turnover is not None:
            if turnover > 1:
                score += 20
            elif turnover > 0.5:
                score += 10
            elif turnover > 0.3:
                score += 0
            else:
                score -= 10

        # Inventory turnover
        inv_turnover = self._safe_float(row, 'inventory_turnover')
        if inv_turnover is not None:
            if inv_turnover > 10:
                score += 15
            elif inv_turnover > 5:
                score += 8
            elif inv_turnover < 2:
                score -= 5

        # Receivable turnover
        recv_turnover = self._safe_float(row, 'receivable_turnover')
        if recv_turnover is not None:
            if recv_turnover > 10:
                score += 15
            elif recv_turnover > 5:
                score += 8
            elif recv_turnover < 2:
                score -= 10

        return max(0, min(100, score))

    def _extract_key_metrics(self, df: pd.DataFrame) -> dict:
        """Extract key financial metrics for display."""
        latest = df.iloc[0]
        prev = df.iloc[min(1, len(df) - 1)] if len(df) > 1 else latest

        return {
            "ROE(%)": self._safe_float(latest, 'roe'),
            "ROA(%)": self._safe_float(latest, 'roa'),
            "毛利率(%)": self._safe_float(latest, 'grossprofit_margin') or self._safe_float(latest, 'gross_margin'),
            "净利率(%)": self._safe_float(latest, 'netprofit_margin') or self._safe_float(latest, 'net_margin'),
            "资产负债率(%)": self._safe_float(latest, 'debt_to_assets') or self._safe_float(latest, 'debt_ratio'),
            "流动比率": self._safe_float(latest, 'current_ratio'),
            "速动比率": self._safe_float(latest, 'quick_ratio'),
            "总资产周转率": self._safe_float(latest, 'asset_turnover'),
            "数据期数": len(df),
        }

    def _generate_summary(self, scores: dict, df: pd.DataFrame) -> str:
        """Generate a natural language summary."""
        total = scores["total_score"]
        rating = scores["rating"]
        metrics = scores["key_metrics"]

        parts = []

        if total >= 85:
            parts.append("公司基本面优秀，各项指标处于行业领先水平。")
        elif total >= 70:
            parts.append("公司基本面良好，整体经营状况健康。")
        elif total >= 55:
            parts.append("公司基本面一般，部分指标有待改善。")
        elif total >= 40:
            parts.append("公司基本面较弱，存在一定经营风险。")
        else:
            parts.append("公司基本面较差，经营风险较高，建议谨慎。")

        roe = metrics.get("ROE(%)")
        if roe is not None:
            parts.append(f"ROE为{roe:.1f}%，{'高于' if roe > 15 else '低于'}行业优秀水平(15%)。")

        debt = metrics.get("资产负债率(%)")
        if debt is not None:
            if debt > 70:
                parts.append(f"资产负债率{debt:.1f}%，财务杠杆偏高，注意偿债风险。")
            elif debt < 30:
                parts.append(f"资产负债率{debt:.1f}%，财务结构保守，偿债能力强。")

        # Growth trend
        if len(df) >= 3:
            rev_key = next((k for k in ['or_yoy', 'total_revenue'] if k in df.columns), None)
            if rev_key:
                recent_vals = [self._safe_float(df.iloc[i], rev_key) for i in range(min(3, len(df)))]
                recent_vals = [v for v in recent_vals if v is not None]
                if len(recent_vals) >= 2 and recent_vals[0] is not None and recent_vals[1] is not None and recent_vals[1] != 0:
                    growth = (recent_vals[0] - recent_vals[1]) / abs(recent_vals[1]) * 100
                    if growth > 0:
                        parts.append(f"最近一期营收同比增长{growth:.1f}%，呈增长态势。")
                    else:
                        parts.append(f"最近一期营收同比下降{abs(growth):.1f}%，需关注收入下滑趋势。")

        return "".join(parts)

    @staticmethod
    def _safe_float(row, key: str) -> Optional[float]:
        """Safely extract a float from a row."""
        try:
            if key not in row.index:
                return None
            val = row[key]
            if pd.isna(val):
                return None
            return float(val)
        except (ValueError, TypeError):
            return None
