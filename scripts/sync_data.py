"""
Data synchronization script.
Downloads and syncs A-share market data to local DuckDB.

Usage:
    python scripts/sync_data.py              # Full incremental sync
    python scripts/sync_data.py --stocks      # Sync stock list only
    python scripts/sync_data.py --quotes      # Sync real-time quotes only
    python scripts/sync_data.py --kline       # Sync K-line incrementally
    python scripts/sync_data.py --full-kline  # Full K-line download (SLOW!)
    python scripts/sync_data.py --symbol 000001  # Sync single stock
"""

import asyncio
import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from data.akshare_client import AKShareClient
from data.duckdb_manager import DuckDBManager
from data.sync_service import DataSyncService
from loguru import logger


async def main():
    """Run data synchronization."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync A-share financial data")
    parser.add_argument("--stocks", action="store_true", help="Sync stock list")
    parser.add_argument("--quotes", action="store_true", help="Sync real-time quotes")
    parser.add_argument("--kline", action="store_true", help="Sync K-line incrementally")
    parser.add_argument("--full-kline", action="store_true", help="Full K-line download (very slow)")
    parser.add_argument("--symbol", type=str, help="Sync single stock K-line")
    parser.add_argument("--full", action="store_true", help="Full sync (all above)")
    args = parser.parse_args()

    # If no flags, do full sync
    if not any([args.stocks, args.quotes, args.kline, args.full_kline, args.symbol, args.full]):
        args.full = True

    # Initialize
    logger.info("=" * 60)
    logger.info("Financial AI Agent - Data Sync")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    db = DuckDBManager()
    db.init_database()

    client = AKShareClient()
    sync = DataSyncService(db, client)

    try:
        if args.full or args.stocks:
            logger.info("--- Syncing stock list ---")
            count = await sync.sync_stock_list()
            logger.info(f"✓ Stock list synced: {count} stocks")

        if args.full or args.quotes:
            logger.info("--- Syncing real-time quotes ---")
            try:
                count = await sync.sync_real_time_quotes()
                logger.info(f"✓ Real-time quotes synced: {count} stocks")
            except Exception as e:
                logger.error(f"✗ Quote sync failed: {e}")

        if args.symbol:
            logger.info(f"--- Syncing K-line for {args.symbol} ---")
            result = await sync.sync_kline_incremental(symbol=args.symbol)
            logger.info(f"✓ K-line sync: {result}")

        elif args.full_kline:
            logger.info("--- Full K-line download (this will take a long time!) ---")
            result = await sync.sync_kline_incremental()
            logger.info(f"✓ Full K-line sync: {result}")

        elif args.full or args.kline:
            logger.info("--- Incremental K-line sync ---")
            result = await sync.sync_kline_incremental()
            logger.info(f"✓ K-line sync: {result}")

        if args.full:
            logger.info("--- Syncing market special data ---")
            try:
                result = await sync.sync_market_special()
                logger.info(f"✓ Market special data synced: {result}")
            except Exception as e:
                logger.error(f"✗ Market special sync failed: {e}")

        # Print stats
        logger.info("=" * 60)
        logger.info("Database Statistics:")
        stats = db.get_db_stats()
        for table, info in stats.items():
            if table != "db_size_mb":
                rows = info.get("rows", 0)
                symbols = info.get("symbols", 0)
                if symbols:
                    logger.info(f"  {table}: {rows} rows, {symbols} symbols")
                else:
                    logger.info(f"  {table}: {rows} rows")
        logger.info(f"  Database size: {stats.get('db_size_mb', 0):.2f} MB")
        logger.info("=" * 60)

    finally:
        db.close()

    logger.info("Sync complete!")


if __name__ == "__main__":
    asyncio.run(main())
