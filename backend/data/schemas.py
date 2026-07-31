"""
Database schemas for the Financial AI Agent.
Defines all table structures for DuckDB storage.
"""

# Database version for migrations
DB_VERSION = 1

# Table DDL statements
DDL_STATEMENTS = {
    "stock_basic": """
        CREATE TABLE IF NOT EXISTS stock_basic (
            symbol      VARCHAR PRIMARY KEY,
            name        VARCHAR NOT NULL,
            exchange    VARCHAR NOT NULL,
            industry    VARCHAR,
            area        VARCHAR,
            list_date   DATE,
            is_st       BOOLEAN DEFAULT FALSE,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,

    "kline_daily": """
        CREATE TABLE IF NOT EXISTS kline_daily (
            symbol      VARCHAR NOT NULL,
            trade_date  DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      DOUBLE,
            amplitude   DOUBLE,
            pct_change  DOUBLE,
            change      DOUBLE,
            turnover    DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """,

    "kline_weekly": """
        CREATE TABLE IF NOT EXISTS kline_weekly (
            symbol      VARCHAR NOT NULL,
            trade_date  DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """,

    "kline_monthly": """
        CREATE TABLE IF NOT EXISTS kline_monthly (
            symbol      VARCHAR NOT NULL,
            trade_date  DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """,

    "real_time_quotes": """
        CREATE TABLE IF NOT EXISTS real_time_quotes (
            symbol          VARCHAR PRIMARY KEY,
            name            VARCHAR,
            price           DOUBLE,
            change          DOUBLE,
            pct_change      DOUBLE,
            open            DOUBLE,
            high            DOUBLE,
            low             DOUBLE,
            volume          BIGINT,
            amount          DOUBLE,
            turnover        DOUBLE,
            pre_close       DOUBLE,
            high_low        DOUBLE,
            total_market_val DOUBLE,
            circulating_market_val DOUBLE,
            pe_ttm          DOUBLE,
            pb              DOUBLE,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,

    "financial_income": """
        CREATE TABLE IF NOT EXISTS financial_income (
            symbol              VARCHAR NOT NULL,
            report_date         DATE NOT NULL,
            total_revenue       DOUBLE,
            operating_revenue   DOUBLE,
            operating_cost      DOUBLE,
            operating_profit    DOUBLE,
            total_profit        DOUBLE,
            net_profit          DOUBLE,
            net_profit_parent   DOUBLE,
            net_profit_deducted DOUBLE,
            eps                 DOUBLE,
            eps_diluted         DOUBLE,
            PRIMARY KEY (symbol, report_date)
        )
    """,

    "financial_balance": """
        CREATE TABLE IF NOT EXISTS financial_balance (
            symbol              VARCHAR NOT NULL,
            report_date         DATE NOT NULL,
            total_assets        DOUBLE,
            total_liabilities   DOUBLE,
            total_equity        DOUBLE,
            equity_parent       DOUBLE,
            current_assets      DOUBLE,
            current_liabilities  DOUBLE,
            cash_equivalents    DOUBLE,
            accounts_receivable DOUBLE,
            inventory           DOUBLE,
            fixed_assets        DOUBLE,
            intangible_assets   DOUBLE,
            goodwill            DOUBLE,
            PRIMARY KEY (symbol, report_date)
        )
    """,

    "financial_cashflow": """
        CREATE TABLE IF NOT EXISTS financial_cashflow (
            symbol                  VARCHAR NOT NULL,
            report_date             DATE NOT NULL,
            cf_operations           DOUBLE,
            cf_operations_sale      DOUBLE,
            cf_investing            DOUBLE,
            cf_financing            DOUBLE,
            cf_free                 DOUBLE,
            net_cf_change           DOUBLE,
            PRIMARY KEY (symbol, report_date)
        )
    """,

    "financial_indicators": """
        CREATE TABLE IF NOT EXISTS financial_indicators (
            symbol          VARCHAR NOT NULL,
            report_date     DATE NOT NULL,
            roe             DOUBLE,
            roe_diluted     DOUBLE,
            roa             DOUBLE,
            gross_margin    DOUBLE,
            net_margin      DOUBLE,
            debt_ratio      DOUBLE,
            current_ratio   DOUBLE,
            quick_ratio     DOUBLE,
            asset_turnover  DOUBLE,
            inventory_turnover DOUBLE,
            receivable_turnover DOUBLE,
            PRIMARY KEY (symbol, report_date)
        )
    """,

    "valuation_daily": """
        CREATE TABLE IF NOT EXISTS valuation_daily (
            symbol          VARCHAR NOT NULL,
            trade_date      DATE NOT NULL,
            pe_ttm          DOUBLE,
            pb              DOUBLE,
            ps_ttm          DOUBLE,
            pcf_ocf_ttm     DOUBLE,
            total_market_val DOUBLE,
            circulating_market_val DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """,

    "index_kline_daily": """
        CREATE TABLE IF NOT EXISTS index_kline_daily (
            symbol      VARCHAR NOT NULL,
            trade_date  DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """,

    "fund_basic": """
        CREATE TABLE IF NOT EXISTS fund_basic (
            fund_code       VARCHAR PRIMARY KEY,
            fund_name       VARCHAR,
            fund_type       VARCHAR,
            establish_date  DATE,
            management_company VARCHAR,
            custodian       VARCHAR,
            fund_size       DOUBLE,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,

    "fund_nav": """
        CREATE TABLE IF NOT EXISTS fund_nav (
            fund_code       VARCHAR NOT NULL,
            nav_date        DATE NOT NULL,
            unit_nav        DOUBLE,
            accumulated_nav DOUBLE,
            daily_return    DOUBLE,
            PRIMARY KEY (fund_code, nav_date)
        )
    """,

    "fund_holdings": """
        CREATE TABLE IF NOT EXISTS fund_holdings (
            fund_code       VARCHAR NOT NULL,
            report_date     DATE NOT NULL,
            stock_symbol    VARCHAR NOT NULL,
            stock_name      VARCHAR,
            holding_amount  BIGINT,
            holding_value   DOUBLE,
            weight_pct      DOUBLE,
            PRIMARY KEY (fund_code, report_date, stock_symbol)
        )
    """,

    "market_calendar": """
        CREATE TABLE IF NOT EXISTS market_calendar (
            trade_date  DATE PRIMARY KEY,
            is_trading  BOOLEAN DEFAULT TRUE,
            week_day    INTEGER,
            holiday_name VARCHAR
        )
    """,

    "limit_up_pool": """
        CREATE TABLE IF NOT EXISTS limit_up_pool (
            trade_date  DATE NOT NULL,
            symbol      VARCHAR NOT NULL,
            name        VARCHAR,
            pct_change  DOUBLE,
            limit_times INTEGER,
            limit_funds BIGINT,
            turnover    DOUBLE,
            float_market_val DOUBLE,
            industry    VARCHAR,
            PRIMARY KEY (trade_date, symbol)
        )
    """,

    "dragon_tiger": """
        CREATE TABLE IF NOT EXISTS dragon_tiger (
            trade_date      DATE NOT NULL,
            symbol          VARCHAR NOT NULL,
            name            VARCHAR,
            reason          VARCHAR,
            buy_amount      DOUBLE,
            sell_amount     DOUBLE,
            net_amount      DOUBLE,
            top_brokers_buy TEXT,
            top_brokers_sell TEXT,
            PRIMARY KEY (trade_date, symbol)
        )
    """,

    "hot_stocks": """
        CREATE TABLE IF NOT EXISTS hot_stocks (
            trade_date  DATE NOT NULL,
            symbol      VARCHAR NOT NULL,
            name        VARCHAR,
            rank        INTEGER,
            hot_score   DOUBLE,
            PRIMARY KEY (trade_date, symbol)
        )
    """,

    "sync_log": """
        CREATE TABLE IF NOT EXISTS sync_log (
            id          BIGINT PRIMARY KEY,
            table_name  VARCHAR NOT NULL,
            symbol      VARCHAR,
            status      VARCHAR,
            rows_count  INTEGER,
            error_msg   VARCHAR,
            started_at  TIMESTAMP,
            finished_at TIMESTAMP
        )
    """,
}

# Index creation statements
INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_kline_symbol ON kline_daily(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_kline_date ON kline_daily(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_kline_sym_date ON kline_daily(symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_index_kline_symbol ON index_kline_daily(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_valuation_date ON valuation_daily(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_income_sym ON financial_income(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_balance_sym ON financial_balance(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_cashflow_sym ON financial_cashflow(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_fund_nav_date ON fund_nav(nav_date);",
    "CREATE INDEX IF NOT EXISTS idx_limit_up_date ON limit_up_pool(trade_date);",
    "CREATE INDEX IF NOT EXISTS idx_hot_stocks_date ON hot_stocks(trade_date);",
]

# Useful views
VIEW_DDL = [
    """
    CREATE VIEW IF NOT EXISTS v_stock_latest AS
    SELECT r.*, b.name, b.industry, b.area
    FROM real_time_quotes r
    JOIN stock_basic b ON r.symbol = b.symbol
    """,

    """
    CREATE VIEW IF NOT EXISTS v_kline_with_ma AS
    SELECT
        symbol, trade_date, open, high, low, close, volume, amount,
        AVG(close) OVER (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS ma5,
        AVG(close) OVER (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS ma10,
        AVG(close) OVER (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma20,
        AVG(close) OVER (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS ma60,
        AVG(volume) OVER (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS vol_ma5
    FROM kline_daily
    """,

    """
    CREATE VIEW IF NOT EXISTS v_latest_financials AS
    SELECT i.*, b.roi, b.debt_ratio, b.current_ratio, b.gross_margin, b.net_margin
    FROM financial_income i
    LEFT JOIN financial_indicators b ON i.symbol = b.symbol AND i.report_date = b.report_date
    WHERE i.report_date = (
        SELECT MAX(report_date) FROM financial_income fi WHERE fi.symbol = i.symbol
    )
    """,
]
