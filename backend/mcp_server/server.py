"""
MCP Server for Financial AI Agent.
Exposes 30+ tools for A-share financial data to AI assistants (Claude, Cursor, etc.).

Supports:
- MCP stdio transport (for local AI tools)
- MCP HTTP/SSE transport (for remote AI tools)

Usage:
    # stdio mode
    python -m backend.mcp_server.server --transport stdio

    # HTTP mode
    python -m backend.mcp_server.server --transport http --port 8001
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.akshare_client import AKShareClient
from data.duckdb_manager import DuckDBManager
from analysis.technical import TechnicalAnalyzer
from analysis.risk import RiskCalculator
from analysis.fundamental import FundamentalAnalyzer
from analysis.valuation import ValuationAnalyzer

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("MCP SDK not found. Install with: pip install mcp")
    sys.exit(1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Initialize MCP Server
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

mcp = FastMCP(
    name="A-Share Financial Agent",
    description="Comprehensive A-share financial data and analysis tools. "
                "Provides real-time quotes, historical K-line, financial statements, "
                "valuation metrics, technical indicators, risk analysis, and market data.",
    version="1.0.0",
)

# Lazy-initialized services (created on first use to avoid module-level leaks)
_db: Optional[DuckDBManager] = None
_client: Optional[AKShareClient] = None
_tech_analyzer: Optional[TechnicalAnalyzer] = None
_risk_calc: Optional[RiskCalculator] = None
_fundamental: Optional[FundamentalAnalyzer] = None
_valuation: Optional[ValuationAnalyzer] = None

# Import validators
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.validators import validate_stock_code, validate_symbols_list, validate_limit


def get_db() -> DuckDBManager:
    global _db
    if _db is None:
        _db = DuckDBManager()
        _db.init_database()
    return _db


def get_client() -> AKShareClient:
    global _client
    if _client is None:
        _client = AKShareClient()
    return _client


def get_tech_analyzer() -> TechnicalAnalyzer:
    global _tech_analyzer
    if _tech_analyzer is None:
        _tech_analyzer = TechnicalAnalyzer()
    return _tech_analyzer


def get_risk_calc() -> RiskCalculator:
    global _risk_calc
    if _risk_calc is None:
        _risk_calc = RiskCalculator()
    return _risk_calc


def get_fundamental() -> FundamentalAnalyzer:
    global _fundamental
    if _fundamental is None:
        _fundamental = FundamentalAnalyzer()
    return _fundamental


def get_valuation() -> ValuationAnalyzer:
    global _valuation
    if _valuation is None:
        _valuation = ValuationAnalyzer()
    return _valuation


def cleanup():
    """Clean up resources on shutdown."""
    global _db
    if _db is not None:
        _db.close()
        _db = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Stock Quotes & Basic Info
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """查询单只A股的最新价格、涨跌幅、成交量等实时行情数据。

    Args:
        symbol: 股票代码，如 '000001' (平安银行), '600519' (贵州茅台)

    Returns:
        JSON格式的实时行情数据，包括最新价、涨跌幅、成交量、换手率等
    """
    try:
        spot = await get_client().get_stock_spot_single(symbol)
        if spot is None:
            # Try from DB
            df = get_db().query(
                "SELECT * FROM v_stock_latest WHERE symbol = ?", [symbol]
            )
            if df.empty:
                return json.dumps(
                    {"error": f"未找到股票 {symbol}，请检查代码是否正确"},
                    ensure_ascii=False,
                )
            spot = df.iloc[0].to_dict()

        # Format nicely
        result = {
            "代码": spot.get("symbol", symbol),
            "名称": spot.get("name", ""),
            "最新价": spot.get("price"),
            "涨跌额": spot.get("change"),
            "涨跌幅(%)": spot.get("pct_change"),
            "今开": spot.get("open"),
            "最高": spot.get("high"),
            "最低": spot.get("low"),
            "昨收": spot.get("pre_close"),
            "成交量(手)": spot.get("volume"),
            "成交额(元)": spot.get("amount"),
            "换手率(%)": spot.get("turnover"),
            "市盈率(TTM)": spot.get("pe_ttm"),
            "市净率": spot.get("pb"),
            "总市值": spot.get("total_market_val"),
            "流通市值": spot.get("circulating_market_val"),
            "更新时间": str(spot.get("updated_at", "")),
        }
        # Remove None values for cleaner output
        result = {k: v for k, v in result.items() if v is not None}
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_stock_prices_batch(symbols: str) -> str:
    """批量查询多只A股的最新价格和涨跌幅。

    Args:
        symbols: 股票代码列表，逗号分隔，如 '000001,600519,300750'
    """
    try:
        sym_list = [s.strip() for s in symbols.split(",")]
        spot_df = await get_client().get_stock_spot()
        result = []
        for sym in sym_list:
            row = spot_df[spot_df['代码'] == sym] if '代码' in spot_df.columns else pd.DataFrame()
            if not row.empty:
                r = row.iloc[0]
                result.append({
                    "代码": r.get("代码", sym),
                    "名称": r.get("名称", ""),
                    "最新价": r.get("最新价"),
                    "涨跌幅(%)": r.get("涨跌幅"),
                    "成交额(亿)": round(r.get("成交额", 0) / 1e8, 2) if r.get("成交额") else None,
                    "市盈率": r.get("市盈率-动态"),
                })

        if not result:
            return json.dumps({"error": "未找到任何股票数据"}, ensure_ascii=False)

        # Sort by absolute change for quick overview
        result.sort(key=lambda x: abs(x.get("涨跌幅(%)", 0) or 0), reverse=True)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def search_stocks(query: str) -> str:
    """按名称或代码搜索A股。

    Args:
        query: 搜索关键词，可以是股票名称或代码片段
    """
    try:
        df = get_db().search_stocks(query, limit=30)
        if df.empty:
            return json.dumps({"message": f"未找到匹配 '{query}' 的股票"}, ensure_ascii=False)

        results = []
        for _, row in df.iterrows():
            results.append({
                "代码": row["symbol"],
                "名称": row["name"],
                "行业": row.get("industry", ""),
                "地区": row.get("area", ""),
                "最新价": row.get("price"),
                "涨跌幅(%)": row.get("pct_change"),
                "市盈率": row.get("pe_ttm"),
                "总市值": row.get("total_market_val"),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: K-Line / Historical Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_kline(
    symbol: str,
    period: str = "daily",
    start_date: str = "",
    end_date: str = "",
    limit: int = 60,
) -> str:
    """获取A股或指数的历史K线数据，用于趋势分析和量化研究。

    Args:
        symbol: 股票代码或指数代码，如 '000001'(平安银行), '000300'(沪深300指数)
        period: K线周期，可选 'daily'(日线), 'weekly'(周线), 'monthly'(月线)
        start_date: 开始日期，格式YYYYMMDD，默认为limit倒数
        end_date: 结束日期，格式YYYYMMDD，默认为今天
        limit: 返回最近N条数据，默认60

    Returns:
        K线数据数组，包含日期、开盘、收盘、最高、最低、成交量、均线等
    """
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=limit * 2)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        # Fetch from AKShare
        if period == "weekly":
            df = await get_client().get_kline_weekly(symbol, start_date, end_date)
        elif period == "monthly":
            df = await get_client().get_kline_monthly(symbol, start_date, end_date)
        else:
            df = await get_client().get_kline_daily(symbol, start_date, end_date)

        if df is None or df.empty:
            return json.dumps({"error": f"未找到 {symbol} 的K线数据"}, ensure_ascii=False)

        # Normalize column names
        col_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '涨跌幅': 'pct_change', '换手率': 'turnover',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Take last N records
        if len(df) > limit:
            df = df.tail(limit)

        # Convert to records
        records = []
        for _, row in df.iterrows():
            records.append({
                "日期": str(row.get("date", "")),
                "开盘": row.get("open"),
                "最高": row.get("high"),
                "最低": row.get("low"),
                "收盘": row.get("close"),
                "成交量": row.get("volume"),
                "成交额": row.get("amount"),
                "涨跌幅(%)": row.get("pct_change"),
                "换手率(%)": row.get("turnover"),
            })

        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"K线查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_kline_with_indicators(
    symbol: str, period: str = "daily", limit: int = 60
) -> str:
    """获取K线数据并附送技术指标：MA5/10/20/60均线，MACD，RSI，KDJ，布林带。

    Args:
        symbol: 股票代码
        period: K线周期
        limit: 返回记录数
    """
    try:
        if not symbol:
            return json.dumps({"error": "请提供股票代码"}, ensure_ascii=False)

        start_date = (datetime.now() - timedelta(days=limit * 3 + 200)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")

        df = await get_client().get_kline_daily(symbol, start_date, end_date)

        if df is None or df.empty:
            return json.dumps({"error": f"未找到 {symbol} 的数据"}, ensure_ascii=False)

        # Normalize
        col_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Calculate technical indicators
        close = df['close'].astype(float)

        # MA
        df['MA5'] = close.rolling(5).mean()
        df['MA10'] = close.rolling(10).mean()
        df['MA20'] = close.rolling(20).mean()
        df['MA60'] = close.rolling(60).mean()

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        df['MACD_DIF'] = ema12 - ema26
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=9).mean()
        df['MACD_BAR'] = 2 * (df['MACD_DIF'] - df['MACD_DEA'])

        # RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # KDJ
        low_n = df['low'].rolling(9).min()
        high_n = df['high'].rolling(9).max()
        h_l_diff = high_n - low_n
        # Prevent divide-by-zero
        rsv = (close - low_n) / h_l_diff.replace(0, float('nan')) * 100
        rsv = rsv.fillna(50)  # Default to middle when no range
        df['KDJ_K'] = rsv.ewm(com=2).mean()
        df['KDJ_D'] = df['KDJ_K'].ewm(com=2).mean()
        df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']

        # Bollinger Bands
        df['BOLL_MID'] = close.rolling(20).mean()
        std = close.rolling(20).std()
        df['BOLL_UP'] = df['BOLL_MID'] + 2 * std
        df['BOLL_DN'] = df['BOLL_MID'] - 2 * std

        # Keep last N
        if len(df) > limit:
            df = df.tail(limit)

        records = []
        for _, row in df.iterrows():
            rec = {
                "日期": str(row.get("date", "")),
                "收盘": row.get("close"),
                "MA5": round(row["MA5"], 2) if pd.notna(row["MA5"]) else None,
                "MA20": round(row["MA20"], 2) if pd.notna(row["MA20"]) else None,
                "MA60": round(row["MA60"], 2) if pd.notna(row["MA60"]) else None,
                "MACD_DIF": round(row["MACD_DIF"], 4) if pd.notna(row["MACD_DIF"]) else None,
                "MACD_DEA": round(row["MACD_DEA"], 4) if pd.notna(row["MACD_DEA"]) else None,
                "RSI": round(row["RSI"], 1) if pd.notna(row["RSI"]) else None,
                "KDJ_K": round(row["KDJ_K"], 1) if pd.notna(row["KDJ_K"]) else None,
                "KDJ_D": round(row["KDJ_D"], 1) if pd.notna(row["KDJ_D"]) else None,
                "KDJ_J": round(row["KDJ_J"], 1) if pd.notna(row["KDJ_J"]) else None,
                "布林上轨": round(row["BOLL_UP"], 2) if pd.notna(row["BOLL_UP"]) else None,
                "布林中轨": round(row["BOLL_MID"], 2) if pd.notna(row["BOLL_MID"]) else None,
                "布林下轨": round(row["BOLL_DN"], 2) if pd.notna(row["BOLL_DN"]) else None,
            }
            records.append(rec)

        # Latest indicators summary
        latest = records[-1] if records else {}
        summary = {
            "股票代码": symbol,
            "最新收盘": latest.get("收盘"),
            "最新日期": latest.get("日期"),
            "技术指标分析": {
                "均线": f"MA5={latest.get('MA5')}, MA20={latest.get('MA20')}, MA60={latest.get('MA60')}",
                "MACD": f"DIF={latest.get('MACD_DIF')}, DEA={latest.get('MACD_DEA')}",
                "RSI(14)": latest.get("RSI"),
                "KDJ": f"K={latest.get('KDJ_K')}, D={latest.get('KDJ_D')}, J={latest.get('KDJ_J')}",
                "布林带": f"上={latest.get('布林上轨')}, 中={latest.get('布林中轨')}, 下={latest.get('布林下轨')}",
            },
            "K线数据": records,
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"技术指标计算失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Financial Statements
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_financials(symbol: str, statement_type: str = "all") -> str:
    """查询上市公司财务报表：利润表、资产负债表、现金流量表和关键财务指标。

    Args:
        symbol: 股票代码
        statement_type: 报表类型，'all'(全部), 'income'(利润表), 'balance'(资产负债表),
                       'cashflow'(现金流量表), 'indicators'(财务指标)
    """
    try:
        if statement_type == "income" or statement_type == "all":
            income_df = await get_client().get_income_statement(symbol)
        if statement_type == "balance" or statement_type == "all":
            balance_df = await get_client().get_balance_sheet(symbol)
        if statement_type == "cashflow" or statement_type == "all":
            cashflow_df = await get_client().get_cashflow(symbol)
        if statement_type == "indicators" or statement_type == "all":
            indicators_df = await get_client().get_financial_indicators(symbol)

        result = {"股票代码": symbol}

        if statement_type in ("income", "all"):
            try:
                if income_df is not None and not income_df.empty:
                    result["利润表(最新)"] = income_df.head(4).to_dict(orient="records")
            except Exception:
                result["利润表(最新)"] = "获取失败"

        if statement_type in ("balance", "all"):
            try:
                if balance_df is not None and not balance_df.empty:
                    result["资产负债表(最新)"] = balance_df.head(4).to_dict(orient="records")
            except Exception:
                result["资产负债表(最新)"] = "获取失败"

        if statement_type in ("cashflow", "all"):
            try:
                if cashflow_df is not None and not cashflow_df.empty:
                    result["现金流量表(最新)"] = cashflow_df.head(4).to_dict(orient="records")
            except Exception:
                result["现金流量表(最新)"] = "获取失败"

        if statement_type in ("indicators", "all"):
            try:
                if indicators_df is not None and not indicators_df.empty:
                    result["财务指标(最新)"] = indicators_df.head(4).to_dict(orient="records")
            except Exception:
                result["财务指标(最新)"] = "获取失败"

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"财务数据查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_financial_summary(symbol: str) -> str:
    """获取上市公司核心财务指标摘要，包括ROE、毛利率、净利率、资产负债率、营收/利润增速等。

    Args:
        symbol: 股票代码
    """
    try:
        score = await get_fundamental().analyze(symbol, client)
        return json.dumps(score, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"财务摘要分析失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Valuation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_valuation(symbol: str) -> str:
    """查询A股估值数据：市盈率(PE)、市净率(PB)、市销率(PS)、市现率(PCF)的历史走势及当前分位。

    Args:
        symbol: 股票代码
    """
    try:
        result = await get_valuation().analyze(symbol, client, db)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"估值查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_valuation_batch(symbols: str) -> str:
    """批量查询多只A股的最新估值快照（PE/PB/PS/PCF）。

    Args:
        symbols: 股票代码列表，逗号分隔，如 '000001,600519,300750'
    """
    try:
        sym_list = [s.strip() for s in symbols.split(",")]
        results = []
        for sym in sym_list:
            try:
                val = await get_valuation().analyze(sym, client, db)
                results.append({
                    "代码": sym,
                    "PE(TTM)": val.get("pe_ttm"),
                    "PE分位": val.get("pe_percentile"),
                    "PB": val.get("pb"),
                    "PB分位": val.get("pb_percentile"),
                    "PS(TTM)": val.get("ps_ttm"),
                    "PCF": val.get("pcf"),
                })
            except Exception as e:
                results.append({"代码": sym, "error": str(e)})

        # Sort by PE
        results.sort(key=lambda x: x.get("PE(TTM)") or 9999)
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"批量估值查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Risk Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def analyze_risk(symbol: str, days: int = 252) -> str:
    """计算投资风险和投资回报率指标：波动率、Beta、夏普比率、最大回撤、VaR、CVaR等。

    Args:
        symbol: 股票代码
        days: 分析周期（交易日），默认252天（约1年）
    """
    try:
        result = await get_risk_calc().analyze(symbol, client, db, days)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"风险分析失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def compare_risk(symbols: str, days: int = 252) -> str:
    """比较多只股票的投资风险和回报指标。

    Args:
        symbols: 股票代码列表，逗号分隔
        days: 分析周期
    """
    try:
        sym_list = [s.strip() for s in symbols.split(",")]
        results = []
        for sym in sym_list:
            try:
                r = await get_risk_calc().analyze(sym, client, db, days)
                results.append({
                    "代码": sym,
                    "名称": r.get("name", ""),
                    "年化波动率(%)": r.get("annualized_volatility"),
                    "Beta": r.get("beta"),
                    "夏普比率": r.get("sharpe_ratio"),
                    "最大回撤(%)": r.get("max_drawdown"),
                    "VaR_95(%)": r.get("var_95"),
                    "年化收益率(%)": r.get("annualized_return"),
                    "卡玛比率": r.get("calmar_ratio"),
                    "胜率(%)": r.get("win_rate"),
                })
            except Exception as e:
                results.append({"代码": sym, "error": str(e)})

        # Sort by Sharpe ratio
        results.sort(
            key=lambda x: x.get("夏普比率") or -999, reverse=True
        )
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"风险比较失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Market Overview & Special Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_market_overview() -> str:
    """获取A股市场总览：涨跌家数、平均涨跌幅、总市值、成交额等。"""
    try:
        spot_df = await get_client().get_stock_spot()
        if spot_df is None or spot_df.empty:
            return json.dumps({"error": "获取市场数据失败"}, ensure_ascii=False)

        total = len(spot_df)
        up_count = len(spot_df[spot_df['涨跌幅'] > 0]) if '涨跌幅' in spot_df.columns else 0
        down_count = len(spot_df[spot_df['涨跌幅'] < 0]) if '涨跌幅' in spot_df.columns else 0
        avg_change = spot_df['涨跌幅'].mean() if '涨跌幅' in spot_df.columns else 0
        total_amount = spot_df['成交额'].sum() if '成交额' in spot_df.columns else 0
        total_mcap = spot_df['总市值'].sum() if '总市值' in spot_df.columns else 0

        # Top gainers & losers
        top_up = spot_df.nlargest(10, '涨跌幅')[['代码', '名称', '最新价', '涨跌幅']].to_dict(orient="records") if '涨跌幅' in spot_df.columns else []
        top_down = spot_df.nsmallest(10, '涨跌幅')[['代码', '名称', '最新价', '涨跌幅']].to_dict(orient="records") if '涨跌幅' in spot_df.columns else []

        result = {
            "市场总览": {
                "股票总数": total,
                "上涨家数": int(up_count),
                "下跌家数": int(down_count),
                "平盘家数": int(total - up_count - down_count),
                "平均涨跌幅(%)": round(float(avg_change), 2),
                "总成交额(亿)": round(float(total_amount) / 1e8, 2) if total_amount else 0,
                "总市值(万亿)": round(float(total_mcap) / 1e12, 2) if total_mcap else 0,
            },
            "涨幅榜前10": top_up,
            "跌幅榜前10": top_down,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"市场总览查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_limit_up_pool(date: str = "") -> str:
    """查询涨停池数据：当日涨停股票、连板数、封单资金、所属板块等。

    Args:
        date: 日期，格式YYYYMMDD，默认今天
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        df = await get_client().get_limit_up_pool(date)
        if df is None or df.empty:
            return json.dumps({"message": f"{date} 无涨停数据或非交易日"}, ensure_ascii=False)

        records = []
        for _, row in df.iterrows():
            records.append({
                "代码": row.get("代码"),
                "名称": row.get("名称"),
                "涨跌幅(%)": row.get("涨跌幅"),
                "连板数": row.get("连板数", 1),
                "封单资金": row.get("封单资金"),
                "换手率(%)": row.get("换手率"),
                "行业": row.get("所属行业"),
            })

        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"涨停池查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_continuous_limit_up() -> str:
    """查询连板天梯：市场高度板、连板晋级情况。"""
    try:
        df = await get_client().get_continuous_limit_up()
        if df is None or df.empty:
            return json.dumps({"message": "暂无连板数据"}, ensure_ascii=False)

        return df.to_json(orient="records", force_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"连板天梯查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_hot_stocks() -> str:
    """查询A股热榜：当前市场关注度最高的股票排名。"""
    try:
        df = await get_client().get_hot_stocks()
        if df is None or df.empty:
            return json.dumps({"message": "暂无热榜数据"}, ensure_ascii=False)

        records = []
        for _, row in df.head(30).iterrows():
            records.append({
                "排名": row.get("排名"),
                "代码": row.get("代码"),
                "名称": row.get("名称"),
                "热度": row.get("热度"),
            })
        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"热榜查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_dragon_tiger() -> str:
    """查询龙虎榜数据：上榜股票、买卖金额、上榜原因、营业部买卖明细。"""
    try:
        df = await get_client().get_dragon_tiger()
        if df is None or df.empty:
            return json.dumps({"message": "暂无龙虎榜数据"}, ensure_ascii=False)

        records = []
        for _, row in df.head(30).iterrows():
            records.append({
                "日期": str(row.get("trade_date", "")),
                "代码": row.get("symbol"),
                "名称": row.get("name"),
                "涨跌幅(%)": row.get("pct_change"),
                "净买额(万)": round(row.get("net_amount", 0) / 10000, 2) if row.get("net_amount") else 0,
                "买入(万)": round(row.get("buy_amount", 0) / 10000, 2) if row.get("buy_amount") else 0,
                "卖出(万)": round(row.get("sell_amount", 0) / 10000, 2) if row.get("sell_amount") else 0,
                "上榜原因": row.get("reason", ""),
            })
        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"龙虎榜查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Index Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_index_quotes() -> str:
    """获取A股主要指数实时行情：上证指数、深证成指、沪深300、创业板指、科创50等。"""
    try:
        df = await get_client().get_index_spot()
        if df is None or df.empty:
            return json.dumps({"error": "获取指数数据失败"}, ensure_ascii=False)

        major_indices = ['000001', '399001', '000300', '399006', '000688', '000016', '399005']

        records = []
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code in major_indices:
                records.append({
                    "代码": code,
                    "名称": row.get("名称", ""),
                    "最新价": row.get("最新价"),
                    "涨跌幅(%)": row.get("涨跌幅"),
                    "涨跌额": row.get("涨跌额"),
                    "成交量": row.get("成交量"),
                    "成交额(亿)": round(row.get("成交额", 0) / 1e8, 2) if row.get("成交额") else 0,
                })

        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"指数查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_index_kline(
    symbol: str = "000300", limit: int = 60
) -> str:
    """获取指数K线数据。

    Args:
        symbol: 指数代码，默认'000300'(沪深300)，可选'000001'(上证指数), '399001'(深证成指), '399006'(创业板指)
        limit: 返回记录数
    """
    try:
        return await get_kline(symbol, "daily", limit=limit)
    except Exception as e:
        return json.dumps({"error": f"指数K线查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Fund Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_fund_nav(fund_code: str) -> str:
    """查询公募基金净值走势。

    Args:
        fund_code: 基金代码，如 '000001'(华夏成长混合)
    """
    try:
        df = await get_client().get_fund_nav(fund_code)
        if df is None or df.empty:
            return json.dumps({"error": f"未找到基金 {fund_code} 的数据"}, ensure_ascii=False)

        records = []
        for _, row in df.tail(60).iterrows():
            records.append({
                "日期": str(row.iloc[0]) if len(row) > 0 else "",
                "单位净值": row.iloc[1] if len(row) > 1 else None,
                "累计净值": row.iloc[2] if len(row) > 2 else None,
            })

        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"基金净值查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_etf_market() -> str:
    """获取ETF场内行情：所有ETF的实时价格、涨跌幅、成交额、折溢价率等。"""
    try:
        df = await get_client().get_etf_spot()
        if df is None or df.empty:
            return json.dumps({"message": "暂无ETF数据"}, ensure_ascii=False)

        records = []
        for _, row in df.head(30).iterrows():
            records.append({
                "代码": row.get("代码"),
                "名称": row.get("名称"),
                "最新价": row.get("最新价"),
                "涨跌幅(%)": row.get("涨跌幅"),
                "成交额(万)": round(row.get("成交额", 0) / 10000, 2) if row.get("成交额") else 0,
            })

        return json.dumps(records, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"ETF查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Peers & Industries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_peer_comparison(symbol: str) -> str:
    """获取同行业可比公司估值对比。

    Args:
        symbol: 股票代码
    """
    try:
        peers = get_db().get_peers(symbol, top_n=20)
        if peers.empty:
            return json.dumps({"message": f"未找到 {symbol} 的同行业公司"}, ensure_ascii=False)

        records = []
        for _, row in peers.iterrows():
            records.append({
                "代码": row["symbol"],
                "名称": row["name"],
                "最新价": row["price"],
                "涨跌幅(%)": row["pct_change"],
                "PE(TTM)": row["pe_ttm"],
                "PB": row["pb"],
                "总市值": row["total_market_val"],
            })

        # Add industry averages
        avg_pe = peers["pe_ttm"].mean() if "pe_ttm" in peers.columns else None
        avg_pb = peers["pb"].mean() if "pb" in peers.columns else None

        return json.dumps({
            "行业": peers.iloc[0].get("industry", "") if not peers.empty else "",
            "可比公司": records,
            "行业平均PE": round(avg_pe, 2) if avg_pe else None,
            "行业平均PB": round(avg_pb, 2) if avg_pb else None,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"同行业比较失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_industry_stocks(industry: str) -> str:
    """查询某个行业板块的所有成分股。

    Args:
        industry: 行业名称，如 '白酒', '新能源汽车', '人工智能', '银行'
    """
    try:
        df = await get_client().get_industry_stocks(industry)
        if df is None or df.empty:
            return json.dumps({"error": f"未找到行业 '{industry}' 的成分股"}, ensure_ascii=False)

        records = []
        for _, row in df.iterrows():
            records.append({
                "代码": row.get("代码"),
                "名称": row.get("名称"),
            })

        return json.dumps({
            "行业": industry,
            "成分股数量": len(records),
            "成分股": records,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"行业成分股查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool: Calendar & Reference
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def get_trade_calendar(year: str = "") -> str:
    """获取交易日历。

    Args:
        year: 年份，如 '2025'，默认当前年份
    """
    try:
        if not year:
            year = str(datetime.now().year)
        df = await get_client().get_trade_calendar()
        return json.dumps({
            "年份": year,
            "交易日数量": len(df) if df is not None else 0,
            "最近交易日": df.iloc[-1].to_dict() if df is not None and not df.empty else {},
        }, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": f"交易日历查询失败: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
async def get_db_statistics() -> str:
    """获取本地数据库统计信息：各表数据量、最新数据日期、数据库大小。"""
    try:
        stats = get_db().get_db_stats()
        return json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"统计查询失败: {str(e)}"}, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry Points
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_stdio():
    """Run MCP server in stdio mode (for Claude Desktop, Cursor, etc.)"""
    logger.info("Starting MCP server in stdio mode...")
    mcp.run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8001):
    """Run MCP server in HTTP/SSE mode."""
    logger.info(f"Starting MCP server in HTTP mode on {host}:{port}...")
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    import argparse
    import signal
    import atexit

    parser = argparse.ArgumentParser(description="A-Share Financial MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=8001, help="HTTP port")

    args = parser.parse_args()

    # Ensure database is initialized
    logger.info("Initializing database...")
    get_db().init_database()

    # Register cleanup on exit
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), exit(0)))

    try:
        if args.transport == "http":
            run_http(args.host, args.port)
        else:
            run_stdio()
    finally:
        cleanup()
