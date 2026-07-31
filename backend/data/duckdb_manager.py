"""
DuckDB database manager for local financial data storage.
Handles connection management, schema creation, upserts, and queries.
Uses read-only connections for read operations to be thread-safe.
"""

import os
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Union

import duckdb
import pandas as pd
import polars as pl
from loguru import logger

from .schemas import DDL_STATEMENTS, INDEX_DDL, VIEW_DDL


class DuckDBManager:
    """Manager for DuckDB financial database operations.

    Uses a connection-per-thread pattern for safety with FastAPI's async threadpool.
    The main connection handles writes; reads use thread-local connections.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv(
                "DUCKDB_PATH",
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "financial_agent.duckdb"),
            )
        self.db_path = os.path.abspath(db_path)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = threading.Lock()
        self._initialized = False

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create the database connection (main write connection)."""
        if self._conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = duckdb.connect(self.db_path)
            # Configure for performance
            self._conn.execute("SET threads = 4")
            self._conn.execute("SET memory_limit = '4GB'")
            self._conn.execute("SET enable_progress_bar = false")
        return self._conn

    @contextmanager
    def read_conn(self):
        """Create a read-only connection for thread-safe queries."""
        read_conn = duckdb.connect(self.db_path, read_only=True)
        try:
            yield read_conn
        finally:
            read_conn.close()

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._initialized = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Schema Management
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def init_database(self):
        """Initialize all tables, indexes, and views. Thread-safe."""
        with self._lock:
            if self._initialized:
                return
            logger.info(f"Initializing DuckDB database at {self.db_path}")

            for table_name, ddl in DDL_STATEMENTS.items():
                try:
                    self.conn.execute(ddl)
                    logger.debug(f"Ensured table: {table_name}")
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")
                    raise

            for idx_ddl in INDEX_DDL:
                try:
                    self.conn.execute(idx_ddl)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")

            for view_ddl in VIEW_DDL:
                try:
                    self.conn.execute(view_ddl)
                except Exception as e:
                    logger.warning(f"View creation warning: {e}")

            self._initialized = True
            logger.info("Database initialization complete.")

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        return result[0] > 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Data Upsert Operations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def upsert_df(
        self,
        table_name: str,
        df: Union[pd.DataFrame, pl.DataFrame],
        primary_keys: list[str] = None,
    ) -> int:
        """
        Upsert a DataFrame into a table using INSERT OR REPLACE.
        Converts Polars to Pandas if needed.
        """
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return 0
        if isinstance(df, pl.DataFrame) and df.is_empty():
            return 0

        # Convert Polars to Pandas (DuckDB's native format)
        if isinstance(df, pl.DataFrame):
            df = df.to_pandas()

        # Register as a temporary view
        self.conn.register("_temp_upsert", df)

        columns = ", ".join(df.columns)
        placeholders = ", ".join(["?" for _ in df.columns])

        if primary_keys:
            # Use DELETE + INSERT for explicit upsert behavior
            pk_conditions = " AND ".join(
                [f"target.{pk} = source.{pk}" for pk in primary_keys]
            )
            sql = f"""
                DELETE FROM {table_name} AS target
                WHERE EXISTS (
                    SELECT 1 FROM _temp_upsert AS source
                    WHERE {pk_conditions}
                );
                INSERT INTO {table_name} ({columns})
                SELECT {columns} FROM _temp_upsert;
            """
            self.conn.execute(sql)
        else:
            # Simple insert
            sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) SELECT {columns} FROM _temp_upsert"
            self.conn.execute(sql)

        self.conn.unregister("_temp_upsert")
        return len(df)

    def upsert_kline(
        self, table_name: str, df: pd.DataFrame, symbol_col: str = "symbol"
    ):
        """Specialized upsert for K-line data with (symbol, date) key."""
        if df is None or df.empty:
            return 0

        self.conn.register("_temp_kline", df)

        sql = f"""
            DELETE FROM {table_name} AS target
            USING _temp_kline AS source
            WHERE target.symbol = source.{symbol_col}
              AND target.trade_date = source.trade_date;

            INSERT INTO {table_name}
            SELECT * FROM _temp_kline;
        """
        self.conn.execute(sql)
        self.conn.unregister("_temp_kline")
        return len(df)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Common Query Methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def query(self, sql: str, params: list = None) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        if params:
            return self.conn.execute(sql, params).df()
        return self.conn.execute(sql).df()

    def query_polars(self, sql: str, params: list = None) -> pl.DataFrame:
        """Execute a SQL query and return results as Polars DataFrame."""
        arrow_table = self.conn.execute(sql, params or []).arrow()
        return pl.from_arrow(arrow_table)

    def get_latest_date(self, table_name: str, date_col: str = "trade_date") -> Optional[datetime]:
        """Get the latest date in a table."""
        result = self.conn.execute(
            f"SELECT MAX({date_col}) FROM {table_name}"
        ).fetchone()
        return result[0] if result[0] else None

    def get_latest_date_for_symbol(self, table_name: str, symbol: str,
                                    date_col: str = "trade_date") -> Optional[datetime]:
        """Get the latest date for a specific symbol in a table."""
        result = self.conn.execute(
            f"SELECT MAX({date_col}) FROM {table_name} WHERE symbol = ?",
            [symbol],
        ).fetchone()
        return result[0] if result[0] else None

    def get_symbol_count(self, table_name: str) -> int:
        """Count distinct symbols in a table."""
        result = self.conn.execute(
            f"SELECT COUNT(DISTINCT symbol) FROM {table_name}"
        ).fetchone()
        return result[0] if result[0] else 0

    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table."""
        result = self.conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()
        return result[0] if result[0] else 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Stock-Specific Queries
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_stock_kline(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        table: str = "v_kline_with_ma",
    ) -> pd.DataFrame:
        """Get K-line data for a stock with optional date filtering."""
        conditions = ["symbol = ?"]
        params = [symbol]

        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)

        where = " AND ".join(conditions)
        return self.conn.execute(
            f"SELECT * FROM {table} WHERE {where} ORDER BY trade_date", params
        ).df()

    def get_stock_financials(self, symbol: str) -> dict:
        """Get all financial statements for a stock."""
        income = self.conn.execute(
            "SELECT * FROM financial_income WHERE symbol = ? ORDER BY report_date DESC",
            [symbol],
        ).df()

        balance = self.conn.execute(
            "SELECT * FROM financial_balance WHERE symbol = ? ORDER BY report_date DESC",
            [symbol],
        ).df()

        cashflow = self.conn.execute(
            "SELECT * FROM financial_cashflow WHERE symbol = ? ORDER BY report_date DESC",
            [symbol],
        ).df()

        indicators = self.conn.execute(
            "SELECT * FROM financial_indicators WHERE symbol = ? ORDER BY report_date DESC",
            [symbol],
        ).df()

        return {
            "income": income,
            "balance": balance,
            "cashflow": cashflow,
            "indicators": indicators,
        }

    def get_stock_valuation(self, symbol: str) -> pd.DataFrame:
        """Get historical valuation data for a stock."""
        return self.conn.execute(
            "SELECT * FROM valuation_daily WHERE symbol = ? ORDER BY trade_date DESC",
            [symbol],
        ).df()

    def get_peers(self, symbol: str, top_n: int = 20) -> pd.DataFrame:
        """Get peer stocks in the same industry."""
        result = self.conn.execute(
            """
            SELECT b.symbol, b.name, b.industry,
                   r.price, r.pct_change, r.pe_ttm, r.pb,
                   r.total_market_val
            FROM stock_basic b
            JOIN real_time_quotes r ON b.symbol = r.symbol
            WHERE b.industry = (
                SELECT industry FROM stock_basic WHERE symbol = ?
            )
            AND b.symbol != ?
            ORDER BY r.total_market_val DESC
            LIMIT ?
            """,
            [symbol, symbol, top_n],
        ).df()

        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Market-Level Queries
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_market_overview(self) -> dict:
        """Get overall market statistics."""
        try:
            stats = self.conn.execute("""
                SELECT
                    COUNT(*) AS total_stocks,
                    SUM(CASE WHEN pct_change > 0 THEN 1 ELSE 0 END) AS up_count,
                    SUM(CASE WHEN pct_change < 0 THEN 1 ELSE 0 END) AS down_count,
                    SUM(CASE WHEN ABS(pct_change) < 0.01 THEN 1 ELSE 0 END) AS flat_count,
                    AVG(pct_change) AS avg_change,
                    SUM(total_market_val) AS total_market_cap
                FROM real_time_quotes
                WHERE price > 0
            """).fetchone()
        except Exception:
            return {}

        return {
            "total_stocks": stats[0],
            "up_count": stats[1],
            "down_count": stats[2],
            "flat_count": stats[3],
            "avg_change_pct": round(stats[4] or 0, 2),
            "total_market_cap": stats[5],
        }

    def get_top_movers(self, direction: str = "up", limit: int = 20) -> pd.DataFrame:
        """Get top gainers or losers."""
        order = "DESC" if direction == "up" else "ASC"
        return self.conn.execute(f"""
            SELECT symbol, name, price, pct_change, change, volume, amount, pe_ttm, pb
            FROM v_stock_latest
            WHERE price > 0 AND pct_change IS NOT NULL
            ORDER BY pct_change {order}
            LIMIT ?
        """, [limit]).df()

    def get_limit_up_pool(self, trade_date: str = None) -> pd.DataFrame:
        """Get limit-up stocks for a date."""
        if trade_date is None:
            trade_date = "SELECT MAX(trade_date) FROM limit_up_pool"
        return self.conn.execute(
            "SELECT * FROM limit_up_pool WHERE trade_date = (?) ORDER BY limit_times DESC",
            [trade_date] if isinstance(trade_date, str) else [],
        ).df()

    def get_hot_ranking(self, trade_date: str = None) -> pd.DataFrame:
        """Get hot stocks ranking."""
        if trade_date is None:
            trade_date = "SELECT MAX(trade_date) FROM hot_stocks"
        return self.conn.execute(
            "SELECT * FROM hot_stocks WHERE trade_date = (?) ORDER BY rank",
            [trade_date] if isinstance(trade_date, str) else [],
        ).df()

    def search_stocks(self, query: str, limit: int = 20) -> pd.DataFrame:
        """Search stocks by symbol or name."""
        return self.conn.execute("""
            SELECT b.symbol, b.name, b.industry, b.area,
                   r.price, r.pct_change, r.pe_ttm, r.total_market_val
            FROM stock_basic b
            LEFT JOIN real_time_quotes r ON b.symbol = r.symbol
            WHERE b.symbol LIKE ? OR b.name LIKE ?
            ORDER BY r.total_market_val DESC NULLS LAST
            LIMIT ?
        """, [f"%{query}%", f"%{query}%", limit]).df()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Export Utilities
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def export_to_parquet(self, query: str, output_path: str, params: list = None):
        """Export query results to a Parquet file."""
        self.conn.execute(
            f"COPY ({query}) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [output_path],
        )

    def export_to_csv(self, query: str, output_path: str, params: list = None):
        """Export query results to a CSV file."""
        self.conn.execute(
            f"COPY ({query}) TO ? (FORMAT CSV, HEADER TRUE)",
            [output_path],
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Database Statistics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_db_stats(self) -> dict:
        """Get database statistics."""
        tables = DDL_STATEMENTS.keys()
        stats = {}
        for table in tables:
            if self.table_exists(table):
                stats[table] = {
                    "rows": self.get_row_count(table),
                    "symbols": self.get_symbol_count(table) if "symbol" in table else None,
                }
        stats["db_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)
        return stats
