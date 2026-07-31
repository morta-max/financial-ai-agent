"""
Download full market data for backtesting, factor research, and AI analysis.
Downloads all A-share daily K-line data and stores in Parquet files.

Usage:
    python scripts/download_market_data.py              # Last 5 years
    python scripts/download_market_data.py --start 20100101  # From 2010
    python scripts/download_market_data.py --output ./my_data/  # Custom output
"""

import asyncio
import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from data.akshare_client import AKShareClient
from data.duckdb_manager import DuckDBManager
from loguru import logger


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Download full A-share market data for analysis"
    )
    parser.add_argument(
        "--start", type=str, default=None,
        help="Start date YYYYMMDD (default: 5 years ago)"
    )
    parser.add_argument(
        "--end", type=str, default=None,
        help="End date YYYYMMDD (default: today)"
    )
    parser.add_argument(
        "--output", type=str, default="./data/parquet/",
        help="Output directory (default: ./data/parquet/)"
    )
    parser.add_argument(
        "--symbols", type=str, default=None,
        help="Comma-separated symbols (default: all A-shares)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=3,
        help="Max concurrent requests (default: 3)"
    )
    args = parser.parse_args()

    if args.start is None:
        # Default: 5 years back
        start = "20200101"
    else:
        start = args.start

    end = args.end or datetime.now().strftime("%Y%m%d")
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 70)
    logger.info("Full Market Data Download")
    logger.info(f"Date range: {start} - {end}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 70)

    client = AKShareClient()

    # Get symbol list
    logger.info("Fetching stock list...")
    spot_df = await client.get_stock_spot()

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        symbols = spot_df['代码'].tolist()
        # Exclude ST and new stocks for faster download
        symbols = [s for s in symbols if not s.startswith('8') and not s.startswith('9')]

    logger.info(f"Will download {len(symbols)} stocks...")

    # Download in batches to avoid memory issues
    BATCH_SIZE = 100
    total_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(symbols))
        batch_symbols = symbols[batch_start:batch_end]

        logger.info(f"Batch {batch_num + 1}/{total_batches}: "
                    f"symbols {batch_start}-{batch_end}")

        data = await client.get_all_stocks_kline_batch(
            batch_symbols, start, end, concurrency=args.concurrency
        )

        # Save batch to Parquet
        if data:
            import pandas as pd
            combined = pd.concat(data.values(), ignore_index=True)
            batch_file = os.path.join(
                output_dir,
                f"kline_daily_batch_{batch_num:04d}_{start}_{end}.parquet"
            )
            combined.to_parquet(batch_file, compression="zstd")
            logger.info(f"  Saved {len(combined)} rows to {batch_file}")

        # Rate limiting between batches
        await asyncio.sleep(2)

    logger.info("=" * 70)
    logger.info("Download complete!")
    logger.info(f"Files saved to: {output_dir}")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
