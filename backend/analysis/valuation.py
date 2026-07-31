"""
Valuation analysis module.
Provides PE/PB/PS/PCF bands, historical percentile ranking, and fair value estimation.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


class ValuationAnalyzer:
    """Analyzer for stock valuation metrics."""

    async def analyze(self, symbol: str, client, db) -> dict:
        """
        Comprehensive valuation analysis for a stock.

        Args:
            symbol: Stock code
            client: AKShareClient instance
            db: DuckDBManager instance

        Returns:
            Valuation analysis result
        """
        try:
            # Get valuation history
            val_df = await client.get_valuation_history(symbol)

            if val_df is None or val_df.empty:
                # Try from database
                val_df = db.get_stock_valuation(symbol)
                if val_df.empty:
                    return {"error": f"无法获取 {symbol} 的估值数据"}

            # Get latest price
            spot = await client.get_stock_spot_single(symbol)

            # Calculate metrics
            result = self._calculate_metrics(val_df, spot)

            result["股票代码"] = symbol
            if spot:
                result["股票名称"] = spot.get("名称", "")
                result["当前价格"] = spot.get("最新价")

            return result

        except Exception as e:
            return {"error": f"估值分析失败: {str(e)}"}

    def _calculate_metrics(self, df: pd.DataFrame, spot: Optional[dict]) -> dict:
        """Calculate valuation metrics from historical data."""
        # Normalize columns
        col_map = {
            '日期': 'date', 'trade_date': 'date',
            '市盈率': 'pe', 'peTTM': 'pe', 'pe_ttm': 'pe',
            '市净率': 'pb', 'pbMRQ': 'pb', 'pb': 'pb',
            '市销率': 'ps', 'psTTM': 'ps', 'ps_ttm': 'ps',
            '市现率': 'pcf', 'pcfTTM': 'pcf', 'pcf_ocf_ttm': 'pcf',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        result = {}

        # PE analysis
        if 'pe' in df.columns:
            pe_data = df['pe'].dropna()
            pe_data = pe_data[pe_data > 0]  # Remove negative PE
            if len(pe_data) > 0:
                current_pe = pe_data.iloc[-1]
                pe_percentile = (pe_data < current_pe).mean() * 100
                result["pe_ttm"] = round(float(current_pe), 2)
                result["pe_percentile"] = round(float(pe_percentile), 1)
                result["pe_min"] = round(float(pe_data.min()), 2)
                result["pe_max"] = round(float(pe_data.max()), 2)
                result["pe_median"] = round(float(pe_data.median()), 2)
                result["pe_avg"] = round(float(pe_data.mean()), 2)
                result["pe_25pct"] = round(float(pe_data.quantile(0.25)), 2)
                result["pe_75pct"] = round(float(pe_data.quantile(0.75)), 2)

                # PE zone
                if pe_percentile < 10:
                    result["pe_zone"] = "极度低估 (低于历史90%时间)"
                elif pe_percentile < 25:
                    result["pe_zone"] = "低估 (低于历史75%时间)"
                elif pe_percentile < 50:
                    result["pe_zone"] = "偏低 (低于历史50%时间)"
                elif pe_percentile < 75:
                    result["pe_zone"] = "偏高 (高于历史50%时间)"
                elif pe_percentile < 90:
                    result["pe_zone"] = "高估 (高于历史75%时间)"
                else:
                    result["pe_zone"] = "极度高估 (高于历史90%时间)"

        # PB analysis
        if 'pb' in df.columns:
            pb_data = df['pb'].dropna()
            pb_data = pb_data[pb_data > 0]
            if len(pb_data) > 0:
                current_pb = pb_data.iloc[-1]
                pb_percentile = (pb_data < current_pb).mean() * 100
                result["pb"] = round(float(current_pb), 2)
                result["pb_percentile"] = round(float(pb_percentile), 1)
                result["pb_min"] = round(float(pb_data.min()), 2)
                result["pb_max"] = round(float(pb_data.max()), 2)
                result["pb_median"] = round(float(pb_data.median()), 2)
                result["pb_avg"] = round(float(pb_data.mean()), 2)
                result["pb_25pct"] = round(float(pb_data.quantile(0.25)), 2)
                result["pb_75pct"] = round(float(pb_data.quantile(0.75)), 2)

                if pb_percentile < 10:
                    result["pb_zone"] = "极度低估"
                elif pb_percentile < 25:
                    result["pb_zone"] = "低估"
                elif pb_percentile < 75:
                    result["pb_zone"] = "合理"
                elif pb_percentile < 90:
                    result["pb_zone"] = "高估"
                else:
                    result["pb_zone"] = "极度高估"

        # PS analysis
        if 'ps' in df.columns:
            ps_data = df['ps'].dropna()
            ps_data = ps_data[ps_data > 0]
            if len(ps_data) > 0:
                current_ps = ps_data.iloc[-1]
                ps_percentile = (ps_data < current_ps).mean() * 100
                result["ps_ttm"] = round(float(current_ps), 2)
                result["ps_percentile"] = round(float(ps_percentile), 1)
                result["ps_avg"] = round(float(ps_data.mean()), 2)

        # PCF analysis
        if 'pcf' in df.columns:
            pcf_data = df['pcf'].dropna()
            pcf_data = pcf_data[pcf_data > 0]
            if len(pcf_data) > 0:
                current_pcf = pcf_data.iloc[-1]
                pcf_percentile = (pcf_data < current_pcf).mean() * 100
                result["pcf"] = round(float(current_pcf), 2)
                result["pcf_percentile"] = round(float(pcf_percentile), 1)

        # Overall valuation score (0-100, higher = more undervalued)
        score = self._calculate_valuation_score(result)
        result["valuation_score"] = score["score"]
        result["valuation_rating"] = score["rating"]
        result["valuation_summary"] = score["summary"]

        return result

    def _calculate_valuation_score(self, metrics: dict) -> dict:
        """Calculate an overall valuation score."""
        score = 50
        signals = []

        # PE contribution
        pe_pct = metrics.get("pe_percentile")
        if pe_pct is not None:
            if pe_pct < 10:
                score += 25
                signals.append("PE处于历史极低位置，估值极具吸引力")
            elif pe_pct < 25:
                score += 15
                signals.append("PE低于历史中枢，估值偏低")
            elif pe_pct < 50:
                score += 5
                signals.append("PE处于历史中位数以下")
            elif pe_pct < 75:
                score -= 5
                signals.append("PE高于历史中枢，估值偏高")
            elif pe_pct < 90:
                score -= 15
                signals.append("PE处于历史高位，估值偏贵")
            else:
                score -= 25
                signals.append("PE处于历史极高水平，估值泡沫风险")

        # PB contribution
        pb_pct = metrics.get("pb_percentile")
        if pb_pct is not None:
            if pb_pct < 10:
                score += 20
                signals.append("PB处于历史底部区域")
            elif pb_pct < 25:
                score += 10
                signals.append("PB低于历史中位数")
            elif pb_pct < 75:
                score += 0
            elif pb_pct < 90:
                score -= 10
                signals.append("PB高于历史中位数")
            else:
                score -= 20
                signals.append("PB处于历史高位")

        # PE absolute level (cross-check)
        pe_ttm = metrics.get("pe_ttm")
        if pe_ttm is not None:
            if pe_ttm > 200:
                score -= 15
                signals.append(f"PE(TTM)={pe_ttm}，绝对估值极高")
            elif pe_ttm > 100:
                score -= 5
            elif 0 < pe_ttm < 10:
                score += 10
                signals.append(f"PE(TTM)={pe_ttm}，绝对估值较低")

        score = max(0, min(100, score))

        if score >= 80:
            rating = "极度低估 ★★★★★"
        elif score >= 65:
            rating = "低估 ★★★★"
        elif score >= 45:
            rating = "合理估值 ★★★"
        elif score >= 30:
            rating = "高估 ★★"
        else:
            rating = "严重高估 ★"

        return {
            "score": round(score, 1),
            "rating": rating,
            "summary": "；".join(signals) if signals else "数据不足，无法判断"
        }

    async def get_valuation_batch(self, symbols: list[str], client, db) -> list[dict]:
        """Batch get valuation snapshots for multiple stocks."""
        results = []
        for sym in symbols:
            try:
                val = await self.analyze(sym, client, db)
                results.append({
                    "代码": sym,
                    "PE(TTM)": val.get("pe_ttm"),
                    "PE分位(%)": val.get("pe_percentile"),
                    "PB": val.get("pb"),
                    "PB分位(%)": val.get("pb_percentile"),
                    "PS(TTM)": val.get("ps_ttm"),
                    "PCF": val.get("pcf"),
                    "估值评级": val.get("valuation_rating"),
                })
            except Exception as e:
                results.append({"代码": sym, "error": str(e)})
        return results
