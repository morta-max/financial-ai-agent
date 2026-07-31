"""
Financial AI Agent - FastAPI Backend Server.

Provides REST API for:
- Stock quotes, K-line data
- Financial statements
- Market overview and special data
- Risk analysis, technical indicators
- Fund data
- AI chat agent endpoint
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.akshare_client import AKShareClient
from data.duckdb_manager import DuckDBManager
from data.sync_service import DataSyncService
from analysis.technical import TechnicalAnalyzer
from analysis.risk import RiskCalculator
from analysis.fundamental import FundamentalAnalyzer
from analysis.valuation import ValuationAnalyzer

# Validators and middleware
from .validators import (
    validate_stock_code, validate_fund_code, validate_date,
    validate_date_range, validate_symbols_list, validate_search_query,
    validate_limit, sanitize_html,
)
from .middleware import (
    rate_limit_middleware, security_headers_middleware,
    request_logging_middleware, get_client_key,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Application Lifecycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

db: DuckDBManager = None
client: AKShareClient = None
sync_service: DataSyncService = None
tech_analyzer: TechnicalAnalyzer = None
risk_calc: RiskCalculator = None
fundamental_analyzer: FundamentalAnalyzer = None
valuation_analyzer: ValuationAnalyzer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    global db, client, sync_service
    global tech_analyzer, risk_calc, fundamental_analyzer, valuation_analyzer

    logger.info("Starting Financial AI Agent API server...")

    # Initialize services
    db = DuckDBManager()
    db.init_database()

    client = AKShareClient()
    sync_service = DataSyncService(db, client)
    tech_analyzer = TechnicalAnalyzer()
    risk_calc = RiskCalculator()
    fundamental_analyzer = FundamentalAnalyzer()
    valuation_analyzer = ValuationAnalyzer()

    # Store in app state for route access
    app.state.db = db
    app.state.client = client
    app.state.sync_service = sync_service
    app.state.tech_analyzer = tech_analyzer
    app.state.risk_calc = risk_calc
    app.state.fundamental_analyzer = fundamental_analyzer
    app.state.valuation_analyzer = valuation_analyzer

    logger.info("All services initialized.")

    yield

    # Cleanup
    if db:
        db.close()
    logger.info("Server shutdown.")


# Create FastAPI app
app = FastAPI(
    title="A-Share Financial AI Agent",
    description="""
    AI-powered financial research and stock analysis platform for A-shares.

    ## Features
    * **实时行情**: 股票最新价格、涨跌幅、成交量
    * **历史K线**: 日线/周线/月线，支持均线、MACD、RSI、KDJ等指标
    * **财务报表**: 利润表、资产负债表、现金流量表、财务指标
    * **估值分析**: PE/PB/PS/PCF历史分位、估值评级
    * **风险分析**: 波动率、Beta、夏普比率、最大回撤、VaR
    * **市场数据**: 涨停池、连板天梯、龙虎榜、热榜
    * **基金数据**: 净值走势、ETF行情、持仓明细
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — use specific origins in production, wildcard for development
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if os.getenv("ENV") == "production" else ["*"],
    allow_credentials=True if os.getenv("ENV") == "production" else False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Limit", "Retry-After"],
    max_age=3600,
)

# Security and utility middleware
app.middleware("http")(request_logging_middleware)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(rate_limit_middleware)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Root & Health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/")
async def root():
    return {
        "name": "A-Share Financial AI Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        db_stats = db.get_db_stats() if db else {}
        return {
            "status": "healthy",
            "database": "connected",
            "db_size_mb": db_stats.get("db_size_mb", 0),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)},
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stock Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/stocks/search")
async def search_stocks(q: str = Query(..., description="搜索关键词"), limit: int = 20):
    """搜索股票（按名称或代码）。"""
    try:
        q = validate_search_query(q)
        limit = validate_limit(limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        df = db.search_stocks(q, limit)
        if df.empty:
            return {"results": [], "query": q}
        return {"results": df.to_dict(orient="records"), "query": q, "total": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="搜索失败，请稍后重试")


@app.get("/api/stocks/{symbol}/quote")
async def get_stock_quote(symbol: str):
    """获取单只股票实时行情。"""
    try:
        symbol = validate_stock_code(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        spot = await client.get_stock_spot_single(symbol)
        if spot is None:
            df = db.query("SELECT * FROM v_stock_latest WHERE symbol = ?", [symbol])
            if df.empty:
                raise HTTPException(status_code=404, detail=f"未找到股票 {symbol}")
            spot = df.iloc[0].to_dict()

        # Clean up non-serializable values
        result = {}
        for k, v in spot.items():
            if pd.isna(v):
                result[k] = None
            elif isinstance(v, (int, float, str, bool)):
                result[k] = v
            elif v is None:
                result[k] = None
            else:
                result[k] = str(v)

        return {"symbol": symbol, "quote": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quote error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="行情数据获取失败，请稍后重试")


@app.get("/api/stocks/{symbol}/kline")
async def get_stock_kline(
    symbol: str,
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    start_date: str = Query(None, description="开始日期 YYYYMMDD"),
    end_date: str = Query(None, description="结束日期 YYYYMMDD"),
    limit: int = Query(60, ge=1, le=1000),
    with_indicators: bool = Query(False, description="是否附带技术指标"),
):
    """获取股票K线数据，可选附送技术指标。"""
    try:
        symbol = validate_stock_code(symbol)
        limit = validate_limit(limit, max_val=500)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        if not start_date:
            start_date = (datetime.now() - timedelta(days=limit * 3 + 200)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")

        if period == "weekly":
            df = await client.get_kline_weekly(symbol, start_date, end_date)
        elif period == "monthly":
            df = await client.get_kline_monthly(symbol, start_date, end_date)
        else:
            df = await client.get_kline_daily(symbol, start_date, end_date)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的K线数据")

        # Normalize
        col_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '涨跌幅': 'pct_change', '换手率': 'turnover',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        if with_indicators and 'close' in df.columns:
            df = _add_technical_indicators(df)

        if len(df) > limit:
            df = df.tail(limit)

        records = df.to_dict(orient="records")
        # Clean NaNs
        for r in records:
            for k, v in list(r.items()):
                if isinstance(v, float) and pd.isna(v):
                    r[k] = None

        return {
            "symbol": symbol,
            "period": period,
            "count": len(records),
            "data": records,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{symbol}/financials")
async def get_stock_financials(symbol: str):
    """获取股票财务报表。"""
    try:
        result = {}
        try:
            income = await client.get_income_statement(symbol)
            if income is not None and not income.empty:
                result["income_statement"] = income.head(8).to_dict(orient="records")
        except Exception as e:
            result["income_statement"] = {"error": str(e)}

        try:
            balance = await client.get_balance_sheet(symbol)
            if balance is not None and not balance.empty:
                result["balance_sheet"] = balance.head(8).to_dict(orient="records")
        except Exception as e:
            result["balance_sheet"] = {"error": str(e)}

        try:
            cashflow = await client.get_cashflow(symbol)
            if cashflow is not None and not cashflow.empty:
                result["cashflow"] = cashflow.head(8).to_dict(orient="records")
        except Exception as e:
            result["cashflow"] = {"error": str(e)}

        try:
            indicators = await client.get_financial_indicators(symbol)
            if indicators is not None and not indicators.empty:
                result["indicators"] = indicators.head(8).to_dict(orient="records")
        except Exception as e:
            result["indicators"] = {"error": str(e)}

        return {"symbol": symbol, "financials": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{symbol}/valuation")
async def get_stock_valuation(symbol: str):
    """获取股票估值分析。"""
    try:
        result = await valuation_analyzer.analyze(symbol, client, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{symbol}/risk")
async def get_stock_risk(
    symbol: str,
    days: int = Query(252, ge=20, le=1260, description="分析周期（交易日）"),
):
    """获取股票风险分析。"""
    try:
        result = await risk_calc.analyze(symbol, client, db, days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{symbol}/peers")
async def get_peer_comparison(symbol: str):
    """获取同行业对比。"""
    try:
        peers = db.get_peers(symbol, top_n=20)
        if peers.empty:
            return {"symbol": symbol, "peers": [], "message": "未找到同行业公司"}

        avg_pe = peers["pe_ttm"].mean()
        avg_pb = peers["pb"].mean()

        return {
            "symbol": symbol,
            "industry": peers.iloc[0].get("industry", ""),
            "peers": peers.to_dict(orient="records"),
            "averages": {
                "pe_ttm": round(float(avg_pe), 2) if not pd.isna(avg_pe) else None,
                "pb": round(float(avg_pb), 2) if not pd.isna(avg_pb) else None,
            },
            "total": len(peers),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Market Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/market/overview")
async def get_market_overview():
    """获取市场总览。"""
    try:
        spot_df = await client.get_stock_spot()
        if spot_df is None or spot_df.empty:
            raise HTTPException(status_code=500, detail="获取市场数据失败")

        total = len(spot_df)
        up_count = len(spot_df[spot_df['涨跌幅'] > 0]) if '涨跌幅' in spot_df.columns else 0
        down_count = len(spot_df[spot_df['涨跌幅'] < 0]) if '涨跌幅' in spot_df.columns else 0
        flat_count = total - up_count - down_count
        avg_change = spot_df['涨跌幅'].mean() if '涨跌幅' in spot_df.columns else 0
        total_amount = spot_df['成交额'].sum() if '成交额' in spot_df.columns else 0
        total_mcap = spot_df['总市值'].sum() if '总市值' in spot_df.columns else 0

        # Top gainers/losers
        top_up = []
        top_down = []
        if '涨跌幅' in spot_df.columns:
            top_up_df = spot_df.nlargest(10, '涨跌幅')
            for _, r in top_up_df.iterrows():
                top_up.append({
                    "symbol": r.get("代码", ""),
                    "name": r.get("名称", ""),
                    "price": r.get("最新价"),
                    "pct_change": r.get("涨跌幅"),
                })

            top_down_df = spot_df.nsmallest(10, '涨跌幅')
            for _, r in top_down_df.iterrows():
                top_down.append({
                    "symbol": r.get("代码", ""),
                    "name": r.get("名称", ""),
                    "price": r.get("最新价"),
                    "pct_change": r.get("涨跌幅"),
                })

        return {
            "market": {
                "total_stocks": int(total),
                "up_count": int(up_count),
                "down_count": int(down_count),
                "flat_count": int(flat_count),
                "avg_change_pct": round(float(avg_change), 2),
                "total_amount_billion": round(float(total_amount) / 1e8, 2) if total_amount else None,
                "total_mcap_trillion": round(float(total_mcap) / 1e12, 2) if total_mcap else None,
            },
            "top_gainers": top_up,
            "top_losers": top_down,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/indexes")
async def get_market_indexes():
    """获取主要指数行情。"""
    try:
        df = await client.get_index_spot()
        if df is None or df.empty:
            raise HTTPException(status_code=500, detail="获取指数数据失败")

        records = []
        for _, row in df.iterrows():
            records.append({
                "code": str(row.get("代码", "")),
                "name": row.get("名称", ""),
                "price": row.get("最新价"),
                "change": row.get("涨跌额"),
                "pct_change": row.get("涨跌幅"),
            })

        return {"indexes": records, "total": len(records)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/limit-up")
async def get_limit_up_pool(date: str = Query(None, description="日期 YYYYMMDD")):
    """获取涨停池。"""
    try:
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        df = await client.get_limit_up_pool(date)
        if df is None or df.empty:
            return {"date": date, "stocks": [], "total": 0}

        records = []
        for _, row in df.iterrows():
            records.append({
                "symbol": row.get("代码", ""),
                "name": row.get("名称", ""),
                "pct_change": row.get("涨跌幅"),
                "limit_times": row.get("连板数", 1),
                "limit_funds": row.get("封单资金"),
                "turnover": row.get("换手率"),
            })

        return {"date": date, "stocks": records, "total": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/hot-stocks")
async def get_hot_stocks():
    """获取热股榜。"""
    try:
        df = await client.get_hot_stocks()
        if df is None or df.empty:
            return {"stocks": [], "total": 0}

        records = []
        for _, row in df.head(30).iterrows():
            records.append({
                "rank": row.get("排名"),
                "symbol": row.get("代码", ""),
                "name": row.get("名称", ""),
                "hot_score": row.get("热度"),
            })

        return {"stocks": records, "total": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/dragon-tiger")
async def get_dragon_tiger():
    """获取龙虎榜。"""
    try:
        df = await client.get_dragon_tiger()
        if df is None or df.empty:
            return {"stocks": [], "total": 0}

        return {"stocks": df.to_dict(orient="records"), "total": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Analysis Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/analysis/compare")
async def compare_stocks(
    symbols: str = Query(..., description="股票代码，逗号分隔"),
    metric: str = Query("risk", description="对比类型: risk, valuation, performance"),
):
    """多只股票对比分析。"""
    try:
        sym_list = [s.strip() for s in symbols.split(",")]

        if metric == "valuation":
            results = await valuation_analyzer.get_valuation_batch(sym_list, client, db)
        elif metric == "risk":
            results = []
            for sym in sym_list:
                try:
                    r = await risk_calc.analyze(sym, client, db, days=252)
                    results.append({
                        "代码": sym,
                        "年化波动率(%)": round(r.get("annualized_volatility", 0) * 100, 2) if r.get("annualized_volatility") else None,
                        "Beta": r.get("beta"),
                        "夏普比率": r.get("sharpe_ratio"),
                        "最大回撤(%)": r.get("max_drawdown", {}).get("max_drawdown_pct") if isinstance(r.get("max_drawdown"), dict) else None,
                        "年化收益率(%)": round(r.get("annualized_return", 0) * 100, 2) if r.get("annualized_return") else None,
                        "风险等级": r.get("风险等级"),
                    })
                except Exception as e:
                    results.append({"代码": sym, "error": str(e)})
        else:
            # Performance comparison
            results = []
            for sym in sym_list:
                try:
                    start_date = (datetime.now() - timedelta(days=504)).strftime("%Y%m%d")
                    end_date = datetime.now().strftime("%Y%m%d")
                    df = await client.get_kline_daily(sym, start_date, end_date)
                    if df is not None and not df.empty:
                        close_col = '收盘' if '收盘' in df.columns else 'close'
                        close = df[close_col].astype(float)
                        ret_1m = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None
                        ret_3m = (close.iloc[-1] / close.iloc[-63] - 1) * 100 if len(close) >= 63 else None
                        ret_1y = (close.iloc[-1] / close.iloc[-252] - 1) * 100 if len(close) >= 252 else None

                        results.append({
                            "代码": sym,
                            "最新价": float(close.iloc[-1]),
                            "近1月收益率(%)": round(ret_1m, 2) if ret_1m else None,
                            "近3月收益率(%)": round(ret_3m, 2) if ret_3m else None,
                            "近1年收益率(%)": round(ret_1y, 2) if ret_1y else None,
                        })
                except Exception as e:
                    results.append({"代码": sym, "error": str(e)})

        return {"metric": metric, "results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fund Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/funds/{fund_code}/nav")
async def get_fund_nav(fund_code: str):
    """获取基金净值数据。"""
    try:
        df = await client.get_fund_nav(fund_code)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"未找到基金 {fund_code}")

        records = []
        for _, row in df.tail(120).iterrows():
            records.append({
                "date": str(row.iloc[0]),
                "unit_nav": row.iloc[1] if len(row) > 1 else None,
                "accumulated_nav": row.iloc[2] if len(row) > 2 else None,
            })

        return {"fund_code": fund_code, "data": records, "count": len(records)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/funds/etf")
async def get_etf_market():
    """获取ETF行情。"""
    try:
        df = await client.get_etf_spot()
        if df is None or df.empty:
            return {"etfs": [], "total": 0}

        return {"etfs": df.head(50).to_dict(orient="records"), "total": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Management Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/admin/sync")
async def trigger_sync(table: str = Query("all", description="同步目标: all, stocks, quotes, kline")):
    """手动触发数据同步。"""
    try:
        if table == "stocks":
            count = await sync_service.sync_stock_list()
            return {"status": "success", "synced": count, "table": "stock_basic"}
        elif table == "quotes":
            count = await sync_service.sync_real_time_quotes()
            return {"status": "success", "synced": count, "table": "real_time_quotes"}
        elif table == "kline":
            result = await sync_service.sync_kline_incremental()
            return {"status": "success", "result": result, "table": "kline_daily"}
        else:
            result = await sync_service.full_sync()
            return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/stats")
async def get_db_stats():
    """获取数据库统计。"""
    try:
        stats = db.get_db_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI Chat / Agent Endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = False


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    AI Chat endpoint for financial analysis.
    Accepts conversation history and returns AI analysis.
    Can be connected to any LLM backend (Claude, GPT, etc.)
    """
    # Extract the last user message
    user_message = req.messages[-1].content if req.messages else ""

    # This is a stub — connect to Claude/GPT for full AI capabilities
    # In production, integrate with Anthropic/OpenAI SDK here

    return {
        "role": "assistant",
        "content": f"""🔍 **金融AI助手分析中...**

您的问题: "{user_message}"

💡 **提示**: 您可以通过以下操作获取数据：

- 📊 查看实时行情: 使用左侧搜索框输入股票代码
- 📈 分析K线走势: 选择股票后查看图表
- 📋 查看财务报表: 在股票详情页切换到"财务"标签
- 🎯 估值分析: 查看PE/PB/PS历史分位
- ⚠️ 风险评估: 查看波动率、夏普比率、最大回撤

如需AI自动分析，请在系统设置中配置LLM API密钥（支持Claude/GPT）。""",
        "suggested_actions": [
            {"type": "search", "label": "搜索股票"},
            {"type": "market_overview", "label": "市场总览"},
            {"type": "hot_stocks", "label": "热门股票"},
        ],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WebSocket for real-time streaming
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.websocket("/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    """WebSocket endpoint for real-time quote streaming."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            # Wait for client message (stock codes to subscribe)
            data = await websocket.receive_json()
            symbols = data.get("symbols", [])

            if not symbols:
                await websocket.send_json({"error": "No symbols provided"})
                continue

            # Fetch real-time quotes
            try:
                spot_df = await client.get_stock_spot()
                results = []
                for sym in symbols:
                    row = spot_df[spot_df['代码'] == sym] if '代码' in spot_df.columns else None
                    if row is not None and not row.empty:
                        r = row.iloc[0]
                        results.append({
                            "symbol": sym,
                            "price": r.get("最新价"),
                            "pct_change": r.get("涨跌幅"),
                            "volume": r.get("成交量"),
                            "timestamp": datetime.now().isoformat(),
                        })
                await websocket.send_json({"quotes": results})
            except Exception as e:
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _add_technical_indicators(df):
    """Add technical indicators to a kline DataFrame."""
    if 'close' not in df.columns:
        return df

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

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float('nan'))
    df['RSI'] = 100 - (100 / (1 + rs))

    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Run Server
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "backend.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
