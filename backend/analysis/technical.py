"""
Technical analysis module for A-share stocks.
Computes: MA, MACD, RSI, KDJ, Bollinger Bands, volume analysis, etc.
"""

import numpy as np
import pandas as pd
from typing import Optional


class TechnicalAnalyzer:
    """Calculator for technical analysis indicators."""

    @staticmethod
    def ma(close: pd.Series, periods: list[int] = None) -> dict:
        """Calculate Moving Averages."""
        if periods is None:
            periods = [5, 10, 20, 60, 120, 250]
        return {f"MA{p}": close.rolling(p).mean() for p in periods}

    @staticmethod
    def ema(close: pd.Series, periods: list[int] = None) -> dict:
        """Calculate Exponential Moving Averages."""
        if periods is None:
            periods = [12, 26]
        return {f"EMA{p}": close.ewm(span=p).mean() for p in periods}

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """Calculate MACD indicator."""
        ema_fast = close.ewm(span=fast).mean()
        ema_slow = close.ewm(span=slow).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal).mean()
        bar = 2 * (dif - dea)

        return {
            "MACD_DIF": dif,
            "MACD_DEA": dea,
            "MACD_BAR": bar,
            "MACD_GOLDEN_CROSS": (dif > dea) & (dif.shift(1) <= dea.shift(1)),
            "MACD_DEATH_CROSS": (dif < dea) & (dif.shift(1) >= dea.shift(1)),
        }

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, k_period: int = 3, d_period: int = 3) -> dict:
        """Calculate KDJ indicator."""
        low_n = low.rolling(n).min()
        high_n = high.rolling(n).max()

        rsv = (close - low_n) / (high_n - low_n).replace(0, np.nan) * 100

        k = rsv.ewm(com=k_period - 1).mean()
        d = k.ewm(com=d_period - 1).mean()
        j = 3 * k - 2 * d

        return {"KDJ_K": k, "KDJ_D": d, "KDJ_J": j}

    @staticmethod
    def bollinger(close: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
        """Calculate Bollinger Bands."""
        mid = close.rolling(period).mean()
        std = close.rolling(period).std()

        return {
            "BOLL_UP": mid + std_dev * std,
            "BOLL_MID": mid,
            "BOLL_DN": mid - std_dev * std,
            "BOLL_WIDTH": (2 * std_dev * std) / mid * 100,  # Bandwidth %
            "BOLL_POSITION": (close - (mid - std_dev * std)) / (2 * std_dev * std),  # %B
        }

    @staticmethod
    def average_true_range(high: pd.Series, low: pd.Series, close: pd.Series,
                           period: int = 14) -> pd.Series:
        """Calculate ATR (Average True Range)."""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=period).mean()

    @staticmethod
    def volume_analysis(close: pd.Series, volume: pd.Series,
                        period: int = 20) -> dict:
        """Analyze volume patterns."""
        vol_ma = volume.rolling(period).mean()
        vol_ratio = volume / vol_ma

        price_up = close > close.shift(1)

        return {
            "VOL_MA": vol_ma,
            "VOL_RATIO": vol_ratio,
            "VOL_UP_DAYS": (vol_ratio > 1.5) & price_up,
            "VOL_DOWN_DAYS": (vol_ratio > 1.5) & ~price_up,
        }

    @staticmethod
    def get_signal_summary(df: pd.DataFrame) -> dict:
        """Generate a technical signal summary from a DataFrame with indicators."""
        if df.empty:
            return {"signal": "无数据", "score": 0}

        latest = df.iloc[-1]
        signals = []
        score = 0

        # MA trend
        if pd.notna(latest.get("MA5")) and pd.notna(latest.get("MA20")):
            if latest["MA5"] > latest["MA20"]:
                signals.append("MA5↑上穿MA20 (短期多头)")
                score += 1
            else:
                signals.append("MA5↓下穿MA20 (短期空头)")
                score -= 1

        # MACD
        if pd.notna(latest.get("MACD_DIF")) and pd.notna(latest.get("MACD_DEA")):
            if latest["MACD_DIF"] > latest["MACD_DEA"]:
                signals.append("MACD金叉 (多头信号)")
                score += 1
            else:
                signals.append("MACD死叉 (空头信号)")
                score -= 1

        # RSI
        rsi_val = latest.get("RSI")
        if pd.notna(rsi_val):
            if rsi_val < 20:
                signals.append(f"RSI={rsi_val:.1f} (超卖区域)")
                score += 2
            elif rsi_val < 30:
                signals.append(f"RSI={rsi_val:.1f} (偏弱)")
                score += 0
            elif rsi_val < 70:
                signals.append(f"RSI={rsi_val:.1f} (正常)")
                score += 0
            elif rsi_val < 80:
                signals.append(f"RSI={rsi_val:.1f} (偏强)")
                score += 0
            else:
                signals.append(f"RSI={rsi_val:.1f} (超买区域)")
                score -= 2

        # KDJ
        k_val = latest.get("KDJ_K")
        d_val = latest.get("KDJ_D")
        if pd.notna(k_val) and pd.notna(d_val):
            if k_val < 20 and d_val < 20:
                signals.append("KDJ超卖 (关注反弹)")
                score += 2
            elif k_val > 80 and d_val > 80:
                signals.append("KDJ超买 (注意回调)")
                score -= 2
            elif k_val > d_val:
                signals.append("KDJ金叉 (短线偏多)")
                score += 1
            else:
                signals.append("KDJ死叉 (短线偏空)")
                score -= 1

        # Bollinger
        close_val = latest.get("close") or latest.get("收盘")
        upper = latest.get("BOLL_UP")
        lower = latest.get("BOLL_DN")
        if pd.notna(close_val) and pd.notna(upper) and pd.notna(lower):
            if close_val > upper:
                signals.append("突破布林上轨 (强势/超买)")
                score += 1
            elif close_val < lower:
                signals.append("跌破布林下轨 (弱势/超卖)")
                score -= 1
            else:
                position = (close_val - lower) / (upper - lower) * 100 if upper != lower else 50
                signals.append(f"布林带位置: {position:.0f}%")

        # Overall signal
        if score >= 4:
            signal = "强烈买入"
        elif score >= 2:
            signal = "偏多"
        elif score > -2:
            signal = "中性/观望"
        elif score > -4:
            signal = "偏空"
        else:
            signal = "强烈卖出"

        return {
            "signal": signal,
            "score": score,
            "indicators": signals,
            "summary": "；".join(signals),
        }
