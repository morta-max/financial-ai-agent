"""
Data synchronization service for incremental updates.
Orchestrates data fetching from AKShare and storage in DuckDB.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from .akshare_client import AKShareClient
from .duckdb_manager import DuckDBManager


class DataSyncService:
    """Service for synchronizing financial data between AKShare and DuckDB."""

    def __init__(self, db: DuckDBManager, client: AKShareClient = None):
        self.db = db
        self.client = client or AKShareClient()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Full Sync Operations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def sync_stock_list(self) -> int:
        """Sync all A-share stock basic info."""
        logger.info("Syncing stock list...")
        try:
            df = await self.client.get_stock_list()
            # Normalize column names
            col_map = {
                '代码': 'symbol', 'code': 'symbol',
                '名称': 'name', 'name': 'name',
            }
            df = df.rename(columns=col_map)

            # Add exchange inference
            df['exchange'] = df['symbol'].apply(self._infer_exchange)
            df['is_st'] = df['name'].str.contains('ST|\\*ST', na=False)
            df['updated_at'] = datetime.now()

            # Keep only needed columns
            cols = ['symbol', 'name', 'exchange']
            for c in ['industry', 'area', 'list_date']:
                if c in df.columns:
                    cols.append(c)
            cols.extend(['is_st', 'updated_at'])
            existing_cols = [c for c in cols if c in df.columns]
            df = df[existing_cols]

            count = self.db.upsert_df("stock_basic", df, primary_keys=["symbol"])
            logger.info(f"Synced {count} stocks")
            return count
        except Exception as e:
            logger.error(f"Stock list sync failed: {e}")
            raise

    async def sync_real_time_quotes(self) -> int:
        """Sync real-time spot quotes for all stocks."""
        logger.info("Syncing real-time quotes...")
        try:
            df = await self.client.get_stock_spot()
            if df is None or df.empty:
                logger.warning("Empty spot data")
                return 0

            # Normalize columns
            col_map = {
                '代码': 'symbol', '名称': 'name', '最新价': 'price',
                '涨跌额': 'change', '涨跌幅': 'pct_change',
                '今开': 'open', '最高': 'high', '最低': 'low',
                '成交量': 'volume', '成交额': 'amount',
                '换手率': 'turnover', '昨收': 'pre_close',
                '振幅': 'high_low',
                '总市值': 'total_market_val', '流通市值': 'circulating_market_val',
                '市盈率-动态': 'pe_ttm', '市净率': 'pb',
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

            df['updated_at'] = datetime.now()
            keep_cols = [v for k, v in col_map.items() if k in df.columns]
            keep_cols.append('updated_at')

            # Also keep any remaining mapped columns
            for c in df.columns:
                if c not in keep_cols and c != 'updated_at':
                    if c in col_map.values():
                        keep_cols.append(c)

            df = df[[c for c in keep_cols if c in df.columns]]
            count = self.db.upsert_df("real_time_quotes", df, primary_keys=["symbol"])
            logger.info(f"Synced {count} real-time quotes")
            return count
        except Exception as e:
            logger.error(f"Real-time quotes sync failed: {e}")
            raise

    async def sync_kline_incremental(
        self, symbol: str = None, symbols: list[str] = None, days_back: int = 30
    ) -> dict:
        """
        Incrementally sync K-line data.
        If symbol provided, sync that one. Otherwise sync all tracked symbols.
        """
        end_date = datetime.now().strftime("%Y%m%d")

        if symbol:
            symbols = [symbol]
        elif symbols is None:
            # Get all symbols from stock_basic
            symbols_df = self.db.query("SELECT symbol FROM stock_basic")
            symbols = symbols_df['symbol'].tolist()

        logger.info(f"Incremental K-line sync for {len(symbols)} symbols...")
        synced = 0
        failed = []

        semaphore = asyncio.Semaphore(5)

        async def sync_one(sym: str):
            nonlocal synced
            async with semaphore:
                try:
                    # Find last date we have data for THIS specific symbol
                    last_date = self.db.get_latest_date_for_symbol(
                        "kline_daily", sym, "trade_date"
                    )
                    if last_date:
                        start_date = (last_date - timedelta(days=days_back)).strftime("%Y%m%d")
                    else:
                        start_date = "20150101"

                    df = await self.client.get_kline_daily(sym, start_date, end_date)

                    if df is not None and not df.empty:
                        # Normalize
                        col_map = {
                            '日期': 'trade_date', '开盘': 'open', '收盘': 'close',
                            '最高': 'high', '最低': 'low', '成交量': 'volume',
                            '成交额': 'amount', '振幅': 'amplitude',
                            '涨跌幅': 'pct_change', '涨跌额': 'change',
                            '换手率': 'turnover',
                        }
                        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                        df['symbol'] = sym

                        self.db.upsert_kline("kline_daily", df)
                        synced += 1
                        return sym
                except Exception as e:
                    logger.error(f"K-line sync failed for {sym}: {e}")
                    failed.append(sym)
                return None

        tasks = [sync_one(s) for s in symbols]
        await asyncio.gather(*tasks)

        logger.info(f"K-line sync complete: {synced} synced, {len(failed)} failed")
        return {"synced": synced, "failed": failed}

    async def sync_market_special(self) -> dict:
        """Sync limit-up pool, hot stocks, dragon & tiger data."""
        logger.info("Syncing market special data...")
        results = {}

        # Limit-up pool
        try:
            df = await self.client.get_limit_up_pool()
            if df is not None and not df.empty:
                trade_date = datetime.now().strftime("%Y-%m-%d")
                df['trade_date'] = trade_date
                col_map = {
                    '代码': 'symbol', '名称': 'name', '涨跌幅': 'pct_change',
                    '连板数': 'limit_times', '封单资金': 'limit_funds',
                    '换手率': 'turnover', '流通市值': 'float_market_val',
                    '所属行业': 'industry',
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                results['limit_up'] = self.db.upsert_df(
                    "limit_up_pool", df, primary_keys=["trade_date", "symbol"]
                )
        except Exception as e:
            logger.warning(f"Limit-up pool sync failed: {e}")

        # Hot stocks
        try:
            df = await self.client.get_hot_stocks()
            if df is not None and not df.empty:
                trade_date = datetime.now().strftime("%Y-%m-%d")
                df['trade_date'] = trade_date
                col_map = {
                    '代码': 'symbol', '名称': 'name', '排名': 'rank', '热度': 'hot_score',
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                results['hot_stocks'] = self.db.upsert_df(
                    "hot_stocks", df, primary_keys=["trade_date", "symbol"]
                )
        except Exception as e:
            logger.warning(f"Hot stocks sync failed: {e}")

        # Dragon & Tiger
        try:
            df = await self.client.get_dragon_tiger()
            if df is not None and not df.empty:
                results['dragon_tiger'] = self.db.upsert_df(
                    "dragon_tiger", df, primary_keys=["trade_date", "symbol"]
                )
        except Exception as e:
            logger.warning(f"Dragon & Tiger sync failed: {e}")

        return results

    async def full_sync(self, include_full_kline: bool = False) -> dict:
        """Perform a full data synchronization."""
        results = {}

        # 1. Stock list
        results['stocks'] = await self.sync_stock_list()

        # 2. Real-time quotes
        try:
            results['quotes'] = await self.sync_real_time_quotes()
        except Exception as e:
            logger.error(f"Quote sync failed: {e}")
            results['quotes'] = 0

        # 3. K-line incremental
        try:
            results['kline'] = await self.sync_kline_incremental()
        except Exception as e:
            logger.error(f"K-line sync failed: {e}")
            results['kline'] = {"synced": 0, "failed": []}

        # 4. Market special data
        try:
            results['special'] = await self.sync_market_special()
        except Exception as e:
            logger.error(f"Market special sync failed: {e}")
            results['special'] = {}

        return results

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _infer_exchange(symbol: str) -> str:
        """Infer exchange from stock symbol."""
        if symbol.startswith(('60', '68')):
            return 'SSE'  # Shanghai
        elif symbol.startswith(('00', '30')):
            return 'SZSE'  # Shenzhen
        elif symbol.startswith(('8', '4')):
            return 'BSE'  # Beijing
        return 'OTHER'
