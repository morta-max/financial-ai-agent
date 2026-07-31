"""
AKShare data client for A-share market data acquisition.
Provides methods for fetching all types of financial data from AKShare.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import akshare as ak
from loguru import logger


class AKShareClient:
    """Client for fetching A-share financial data via AKShare."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _retry_wrapper(self, func, *args, **kwargs):
        """Wrap sync AKShare calls with retry logic."""
        for attempt in range(self.max_retries):
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: func(*args, **kwargs)
                )
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"AKShare call failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"AKShare call failed after {self.max_retries} attempts: {e}")
                    raise

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Basic Stock Info
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_stock_list(self) -> pd.DataFrame:
        """Get all A-share stock basic information."""
        try:
            df = await self._retry_wrapper(ak.stock_info_a_code_name)
            if df is None or df.empty:
                raise ValueError("Empty response from stock_info_a_code_name")
            return df
        except Exception as e:
            logger.error(f"AKShare stock list failed: {e}")
            # Fallback: use stock_zh_a_spot_em to get current stocks
            try:
                df = await self._retry_wrapper(ak.stock_zh_a_spot_em)
                if df is not None and not df.empty:
                    df = df[['代码', '名称']].rename(
                        columns={'代码': 'code', '名称': 'name'}
                    )
                    return df
            except Exception as fallback_e:
                logger.error(f"Fallback also failed: {fallback_e}")
                raise

    async def get_stock_spot(self) -> pd.DataFrame:
        """Get real-time spot quotes for ALL A-shares."""
        return await self._retry_wrapper(ak.stock_zh_a_spot_em)

    async def get_stock_spot_single(self, symbol: str) -> Optional[dict]:
        """Get real-time quote for a single stock."""
        df = await self.get_stock_spot()
        row = df[df['代码'] == symbol]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # K-Line Data (Historical Prices)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_kline_daily(
        self,
        symbol: str,
        start_date: str = "20200101",
        end_date: str = None,
        adjust: str = "qfq"  # qfq=前复权, hfq=后复权, ""=不复权
    ) -> pd.DataFrame:
        """Get daily K-line data for a single stock."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        return await self._retry_wrapper(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    async def get_kline_weekly(
        self,
        symbol: str,
        start_date: str = "20200101",
        end_date: str = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Get weekly K-line data."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        return await self._retry_wrapper(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="weekly",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    async def get_kline_monthly(
        self,
        symbol: str,
        start_date: str = "20200101",
        end_date: str = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Get monthly K-line data."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        return await self._retry_wrapper(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="monthly",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Index Data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_index_kline(
        self,
        symbol: str,  # e.g. "000300" for CSI 300
        start_date: str = "20200101",
        end_date: str = None,
    ) -> pd.DataFrame:
        """Get index K-line data."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        return await self._retry_wrapper(
            ak.stock_zh_index_daily_em,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_index_spot(self) -> pd.DataFrame:
        """Get real-time index quotes."""
        return await self._retry_wrapper(ak.stock_zh_index_spot_em)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Financial Statements
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """Get income statement (利润表)."""
        return await self._retry_wrapper(
            ak.stock_financial_abstract_ths, symbol=symbol, indicator="按报告期"
        )

    async def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Get balance sheet (资产负债表)."""
        return await self._retry_wrapper(
            ak.stock_financial_balance_sheet_by_report_ths, symbol=symbol
        )

    async def get_cashflow(self, symbol: str) -> pd.DataFrame:
        """Get cash flow statement (现金流量表)."""
        return await self._retry_wrapper(
            ak.stock_financial_cash_flow_by_report_ths, symbol=symbol
        )

    async def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """Get key financial indicators."""
        return await self._retry_wrapper(
            ak.stock_financial_analysis_indicator, symbol=symbol
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Valuation Data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_valuation_history(self, symbol: str) -> pd.DataFrame:
        """Get historical PE/PB/PS/PCF data for a stock."""
        return await self._retry_wrapper(
            ak.stock_a_lg_indicator, symbol=symbol
        )

    async def get_market_valuation(self) -> pd.DataFrame:
        """Get all stocks' latest valuation metrics."""
        return await self._retry_wrapper(ak.stock_a_pe)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Market Special Data (同花顺特色数据)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_limit_up_pool(self, trade_date: str = None) -> pd.DataFrame:
        """Get limit-up stocks pool (涨停池)."""
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")
        return await self._retry_wrapper(
            ak.stock_zt_pool_em, date=trade_date
        )

    async def get_continuous_limit_up(self) -> pd.DataFrame:
        """Get continuous limit-up stocks (连板天梯)."""
        return await self._retry_wrapper(ak.stock_zt_pool_zbgc_em)

    async def get_dragon_tiger(self) -> pd.DataFrame:
        """Get dragon & tiger board data (龙虎榜)."""
        return await self._retry_wrapper(ak.stock_dzjy_hygtj)

    async def get_hot_stocks(self) -> pd.DataFrame:
        """Get hot stocks ranking."""
        return await self._retry_wrapper(ak.stock_hot_rank_em)

    async def get_stock_changes(self, symbol: str) -> pd.DataFrame:
        """Get stock abnormal changes (异动)."""
        return await self._retry_wrapper(
            ak.stock_changes_em, symbol=symbol
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Fund Data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_fund_list(self) -> pd.DataFrame:
        """Get all public fund basic info."""
        return await self._retry_wrapper(ak.fund_name_em)

    async def get_fund_nav(self, fund_code: str) -> pd.DataFrame:
        """Get fund NAV history."""
        return await self._retry_wrapper(
            ak.fund_open_fund_info_em,
            symbol=fund_code,
            indicator="单位净值走势",
        )

    async def get_fund_holdings(self, fund_code: str, year: str = "2024") -> pd.DataFrame:
        """Get fund stock holdings."""
        return await self._retry_wrapper(
            ak.fund_portfolio_hold_detail_em,
            symbol=fund_code,
            date=year,
        )

    async def get_etf_spot(self) -> pd.DataFrame:
        """Get ETF real-time quotes."""
        return await self._retry_wrapper(ak.fund_etf_spot_em)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Market Calendar & Reference
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_trade_calendar(self) -> pd.DataFrame:
        """Get trading calendar."""
        return await self._retry_wrapper(ak.tool_trade_date_hist_sina)

    async def get_industry_classification(self) -> pd.DataFrame:
        """Get industry classifications."""
        return await self._retry_wrapper(ak.stock_board_industry_name_em)

    async def get_industry_stocks(self, industry: str) -> pd.DataFrame:
        """Get stocks in an industry."""
        return await self._retry_wrapper(
            ak.stock_board_industry_cons_em, symbol=industry
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Bulk / Full Market Data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_all_stocks_kline_batch(
        self,
        symbols: list[str],
        start_date: str = "20200101",
        end_date: str = None,
        adjust: str = "qfq",
        concurrency: int = 5,
    ) -> dict[str, pd.DataFrame]:
        """Fetch K-line data for multiple stocks with concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(symbol: str):
            async with semaphore:
                try:
                    return symbol, await self.get_kline_daily(
                        symbol, start_date, end_date, adjust
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch {symbol}: {e}")
                    return symbol, None

        tasks = [fetch_one(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return {sym: df for sym, df in results if df is not None}

    async def download_full_market(
        self,
        start_date: str = "20150101",
        end_date: str = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        Download full market daily K-line data.
        WARNING: This is rate-limited. Use for initial data load only.
        """
        spot_df = await self.get_stock_spot()
        symbols = spot_df['代码'].tolist()
        logger.info(f"Downloading full market data for {len(symbols)} stocks...")

        all_data = []
        failed = []

        semaphore = asyncio.Semaphore(3)  # Very conservative rate limit

        async def fetch_one(symbol: str):
            async with semaphore:
                try:
                    df = await self.get_kline_daily(symbol, start_date, end_date, adjust)
                    if df is not None and not df.empty:
                        df['symbol'] = symbol
                        return df
                except Exception as e:
                    failed.append(symbol)
                    logger.warning(f"Skipping {symbol}: {e}")
                return None

        tasks = [fetch_one(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        for df in results:
            if df is not None:
                all_data.append(df)

        logger.info(
            f"Downloaded {len(all_data)} stocks, failed: {len(failed)}"
        )
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
