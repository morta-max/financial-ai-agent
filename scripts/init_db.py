"""
Initialize the DuckDB database for the Financial AI Agent.
Creates all tables, indexes, and views.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from data.duckdb_manager import DuckDBManager
from loguru import logger


def main():
    """Initialize the database."""
    db_path = os.getenv(
        "DUCKDB_PATH",
        os.path.join(os.path.dirname(__file__), "..", "data", "financial_agent.duckdb"),
    )
    db_path = os.path.abspath(db_path)

    logger.info(f"Initializing database at: {db_path}")

    with DuckDBManager(db_path) as db:
        db.init_database()

        # Verify
        stats = db.get_db_stats()
        logger.info(f"Database initialized successfully!")
        logger.info(f"Tables created: {len(stats) - 1}")  # -1 for db_size
        logger.info(f"Database size: {stats.get('db_size_mb', 0):.2f} MB")

        # Print table list
        for table, info in stats.items():
            if table != "db_size_mb":
                rows = info.get("rows", 0)
                logger.info(f"  {table}: {rows} rows")


if __name__ == "__main__":
    main()
