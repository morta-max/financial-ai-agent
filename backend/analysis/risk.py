"""
Investment risk and return analysis module.
Calculates volatility, Beta, Sharpe ratio, VaR, drawdown, etc.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


class RiskCalculator:
    """Calculator for investment risk and return metrics."""

    @staticmethod
    def calculate_returns(prices: pd.Series) -> pd.Series:
        """Calculate daily simple (arithmetic) returns from price series."""
        return prices.pct_change().dropna()

    @staticmethod
    def calculate_log_returns(prices: pd.Series) -> pd.Series:
        """Calculate daily log returns from price series."""
        return np.log(prices / prices.shift(1)).dropna()

    @staticmethod
    def annualized_return(returns: pd.Series, trading_days: int = 252) -> float:
        """Calculate annualized return from arithmetic daily returns."""
        if len(returns) == 0:
            return 0.0
        total_return = (1 + returns).prod() - 1
        years = len(returns) / trading_days
        if years <= 0:
            return 0.0
        # Handle negative total return
        if total_return <= -1:
            return -1.0
        return (1 + total_return) ** (1 / years) - 1

    @staticmethod
    def annualized_volatility(returns: pd.Series, trading_days: int = 252) -> float:
        """Calculate annualized volatility."""
        if len(returns) < 2:
            return 0.0
        return returns.std() * np.sqrt(trading_days)

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02,
                     trading_days: int = 252) -> float:
        """Calculate Sharpe ratio."""
        ann_return = RiskCalculator.annualized_return(returns, trading_days)
        ann_vol = RiskCalculator.annualized_volatility(returns, trading_days)
        if ann_vol == 0:
            return 0.0
        return (ann_return - risk_free_rate) / ann_vol

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02,
                      trading_days: int = 252) -> float:
        """Calculate Sortino ratio (uses downside deviation only)."""
        downside = returns[returns < 0]
        if len(downside) < 2:
            return 0.0
        downside_std = downside.std() * np.sqrt(trading_days)
        ann_return = RiskCalculator.annualized_return(returns, trading_days)
        if downside_std == 0:
            return 0.0
        return (ann_return - risk_free_rate) / downside_std

    @staticmethod
    def max_drawdown(prices: pd.Series) -> dict:
        """Calculate maximum drawdown with dates."""
        if len(prices) < 2:
            return {"max_drawdown": 0.0, "peak_date": None, "trough_date": None,
                    "recovery_date": None}

        cumulative_max = prices.cummax()
        drawdown = (prices - cumulative_max) / cumulative_max

        max_dd = drawdown.min()
        max_dd_end = drawdown.idxmin()

        # Find the peak before the trough
        peak_idx = cumulative_max.loc[:max_dd_end].idxmax() if hasattr(cumulative_max, 'loc') else None

        # Find recovery
        recovery = None
        if max_dd < 0:
            after_trough = prices.loc[max_dd_end:]
            recovered = after_trough[after_trough >= cumulative_max.loc[max_dd_end]]
            if not recovered.empty and hasattr(recovered, 'index'):
                recovery = recovered.index[0]

        return {
            "max_drawdown": float(max_dd),
            "max_drawdown_pct": round(float(max_dd) * 100, 2),
            "peak_date": str(peak_idx) if peak_idx else None,
            "trough_date": str(max_dd_end),
            "recovery_date": str(recovery) if recovery else None,
        }

    @staticmethod
    def var_cvar(returns: pd.Series, confidence: float = 0.95) -> dict:
        """Calculate Value-at-Risk and Conditional VaR."""
        if len(returns) < 10:
            return {"VaR_95": 0.0, "CVaR_95": 0.0}

        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()

        return {
            "VaR_95": round(float(var) * 100, 2),  # as percentage
            "CVaR_95": round(float(cvar) * 100, 2),  # as percentage
            "VaR_99": round(float(np.percentile(returns, 1)) * 100, 2),
        }

    @staticmethod
    def beta_alpha(returns: pd.Series, benchmark_returns: pd.Series,
                   risk_free_rate: float = 0.02, trading_days: int = 252) -> dict:
        """Calculate Beta and Alpha vs benchmark."""
        common_idx = returns.index.intersection(benchmark_returns.index)
        if len(common_idx) < 20:
            return {"beta": None, "alpha": None, "r_squared": None}

        r = returns.loc[common_idx]
        b = benchmark_returns.loc[common_idx]

        cov = r.cov(b)
        var = b.var()

        if var == 0:
            return {"beta": None, "alpha": None, "r_squared": None}

        beta = cov / var
        alpha = RiskCalculator.annualized_return(r, trading_days) - (
            risk_free_rate + beta * (RiskCalculator.annualized_return(b, trading_days) - risk_free_rate)
        )
        correlation = r.corr(b)
        r_squared = correlation ** 2

        return {
            "beta": round(float(beta), 3),
            "alpha": round(float(alpha) * 100, 2),  # Annualized alpha %
            "r_squared": round(float(r_squared), 3),
            "correlation": round(float(correlation), 3),
        }

    @staticmethod
    def win_rate(returns: pd.Series) -> dict:
        """Calculate win rate and related metrics."""
        if len(returns) == 0:
            return {"win_rate": 0, "avg_win": 0, "avg_loss": 0, "profit_factor": 0}

        wins = returns[returns > 0]
        losses = returns[returns < 0]

        win_rate = len(wins) / len(returns) * 100
        avg_win = wins.mean() * 100 if len(wins) > 0 else 0
        avg_loss = losses.mean() * 100 if len(losses) > 0 else 0

        total_wins = wins.sum()
        total_losses = abs(losses.sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        return {
            "win_rate(%)": round(win_rate, 1),
            "avg_win(%)": round(avg_win, 2),
            "avg_loss(%)": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": len(returns),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
        }

    @staticmethod
    def calmar_ratio(returns: pd.Series, prices: pd.Series,
                     trading_days: int = 252) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        ann_return = RiskCalculator.annualized_return(returns, trading_days)
        dd = RiskCalculator.max_drawdown(prices)
        max_dd = dd['max_drawdown']
        if max_dd == 0:
            return 0.0
        return ann_return / abs(max_dd)

    @staticmethod
    def information_ratio(returns: pd.Series, benchmark_returns: pd.Series,
                          trading_days: int = 252) -> float:
        """Calculate Information Ratio."""
        common_idx = returns.index.intersection(benchmark_returns.index)
        if len(common_idx) < 20:
            return 0.0

        excess = returns.loc[common_idx] - benchmark_returns.loc[common_idx]
        if excess.std() == 0:
            return 0.0

        return (excess.mean() / excess.std()) * np.sqrt(trading_days)

    async def analyze(self, symbol: str, client, db, days: int = 252,
                      benchmark_symbol: str = "000300") -> dict:
        """
        Comprehensive risk and return analysis for a stock.

        Args:
            symbol: Stock code
            client: AKShareClient instance
            db: DuckDBManager instance
            days: Lookback period (trading days)
            benchmark_symbol: Benchmark index code

        Returns:
            Dictionary with all risk/return metrics
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        # Get stock data
        df = await client.get_kline_daily(symbol, start_date, end_date)

        if df is None or df.empty:
            return {"error": f"无法获取 {symbol} 的行情数据"}

        # Normalize columns
        col_map = {'日期': 'date', '收盘': 'close'}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        close = df['close'].astype(float)
        returns = self.calculate_returns(close)

        if len(returns) < 20:
            return {"error": f"数据不足（仅{len(returns)}条），需要至少20个交易日"}

        # Basic metrics
        ann_vol = self.annualized_volatility(returns)
        ann_ret = self.annualized_return(returns)
        sharpe = self.sharpe_ratio(returns)
        sortino = self.sortino_ratio(returns)
        dd = self.max_drawdown(close)
        var_metrics = self.var_cvar(returns)
        wr = self.win_rate(returns)
        calmar = self.calmar_ratio(returns, close)

        # Benchmark comparison
        try:
            bench_df = await client.get_index_kline(
                benchmark_symbol, start_date, end_date
            )
            if bench_df is not None and not bench_df.empty:
                bench_close_col = '收盘' if '收盘' in bench_df.columns else 'close'
                if bench_close_col in bench_df.columns:
                    bench_close = bench_df[bench_close_col].astype(float)
                    bench_returns = self.calculate_returns(bench_close)
                    ba = self.beta_alpha(returns, bench_returns)
                    ir = self.information_ratio(returns, bench_returns)
                else:
                    ba = {"beta": None, "alpha": None, "r_squared": None}
                    ir = None
            else:
                ba = {"beta": None, "alpha": None, "r_squared": None}
                ir = None
        except Exception:
            ba = {"beta": None, "alpha": None, "r_squared": None}
            ir = None

        # Additional stats
        cumulative_return = (1 + returns).prod() - 1
        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        best_day = returns.max() * 100
        worst_day = returns.min() * 100
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # Risk grade
        if ann_vol < 0.2:
            risk_level = "低风险"
        elif ann_vol < 0.35:
            risk_level = "中等风险"
        elif ann_vol < 0.5:
            risk_level = "高风险"
        else:
            risk_level = "极高风险"

        # Overall score (0-100)
        score = 50
        if sharpe > 1:
            score += 15
        elif sharpe > 0.5:
            score += 8
        elif sharpe < 0:
            score -= 15

        if dd['max_drawdown'] > -0.15:
            score += 10
        elif dd['max_drawdown'] < -0.35:
            score -= 10

        if calmar > 1:
            score += 10
        if ann_vol < 0.25:
            score += 10
        if wr['win_rate(%)'] > 55:
            score += 5
        score = max(0, min(100, score))

        return {
            "股票代码": symbol,
            "分析周期": f"{days}个交易日",
            "数据范围": f"{df['date'].iloc[0]} 至 {df['date'].iloc[-1]}",
            "风险等级": risk_level,
            "综合评分": score,

            "收益指标": {
                "累计收益率(%)": round(float(cumulative_return) * 100, 2),
                "年化收益率(%)": round(float(ann_ret) * 100, 2),
                "最佳日收益(%)": round(float(best_day), 2),
                "最差日收益(%)": round(float(worst_day), 2),
                "上涨天数": int(positive_days),
                "下跌天数": int(negative_days),
                "胜率": wr,
            },

            "风险指标": {
                "年化波动率(%)": round(float(ann_vol) * 100, 2),
                "最大回撤": dd,
                "VaR/CVaR": var_metrics,
                "偏度": round(float(skewness), 3),
                "峰度": round(float(kurtosis), 3),
            },

            "风险调整收益": {
                "夏普比率": round(float(sharpe), 3),
                "索提诺比率": round(float(sortino), 3),
                "卡玛比率": round(float(calmar), 3),
                "信息比率": round(float(ir), 3) if ir else None,
            },

            "基准对比": {
                "基准指数": benchmark_symbol,
                "Beta": ba.get("beta"),
                "Alpha(%)": ba.get("alpha"),
                "R²": ba.get("r_squared"),
                "相关性": ba.get("correlation"),
            },

            "最新价格": float(close.iloc[-1]),
            "分析时间": datetime.now().isoformat(),
        }
