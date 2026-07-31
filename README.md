# 📊 A-Share Financial AI Agent

> AI-powered financial research and stock analysis platform for Chinese A-shares.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io/)

A comprehensive AI agent platform that provides real-time A-share market data, technical analysis, fundamental analysis, valuation, risk assessment, and more — all accessible through a chat interface, REST API, and MCP (Model Context Protocol) server.

---

## ✨ Features

### 📈 Market Data
- **Real-time quotes** — Price, change %, volume, turnover for all A-shares
- **K-line data** — Daily/weekly/monthly with forward/backward adjusted prices
- **Index data** — SSE Composite, CSI 300, ChiNext, STAR 50, and more
- **Financial statements** — Income, balance sheet, cash flow, key indicators
- **Valuation** — PE/PB/PS/PCF historical bands with percentile ranking

### 🔬 Analysis Engine
- **Technical indicators** — MA, MACD, RSI, KDJ, Bollinger Bands, ATR
- **Fundamental scoring** — Profitability, growth, solvency, efficiency (0-100)
- **Risk metrics** — Volatility, Beta, Sharpe/Sortino/Calmar ratios, VaR/CVaR, Max Drawdown
- **Peer comparison** — Industry-relative valuation comparison

### 🚀 Special Market Data
- **Limit-up pool** (涨停池) — Daily limit-up stocks with consecutive board count
- **Continuous limit-up ladder** (连板天梯) — Market height board tracking
- **Dragon & Tiger board** (龙虎榜) — Institutional trading activity
- **Hot stocks ranking** (热榜) — Market attention leaderboard

### 💰 Fund Data
- **Public fund NAV** — Historical net value tracking
- **ETF market** — Real-time ETF quotes and premiums
- **Fund holdings** — Portfolio disclosure data

### 🧠 AI Integration
- **MCP Server** — 30+ tools for Claude, Cursor, Windsurf, and other AI assistants
- **Chat interface** — Natural language queries with generative UI components
- **Dual-mode** — stdio (local) and HTTP/SSE (remote) MCP transport

### 💾 Data Architecture
- **DuckDB** — Embedded columnar database for local analytics
- **Parquet export** — Efficient data format for backtesting and research
- **Incremental sync** — Smart upserts to keep data fresh

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                          │
│  Chat UI + Generative Components (Stock Cards, Charts, etc.) │
│  useChat() → toolInvocations → React Components             │
└──────────┬───────────────────────────────────────────────────┘
           │ HTTP/REST              │ WebSocket
┌──────────▼───────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  REST API: /api/stocks, /api/market, /api/analysis, etc.    │
│  WebSocket: /ws/quotes (real-time streaming)                │
└──────────┬───────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────┐
│              Analysis Engine (Python)                        │
│  Technical · Fundamental · Risk · Valuation                 │
└──────────┬───────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────┐
│              Data Layer (Python)                             │
│  AKShare Client ←→ DuckDB Manager ←→ Sync Service          │
└──────────┬───────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────┐
│              MCP Server (Python)                             │
│  30+ Tools · stdio + HTTP/SSE · Claude/Cursor/Windsurf      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn

### 1. Clone and setup

```bash
cd financial-ai-agent

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

### 2. Initialize database

```bash
cd ..
python scripts/init_db.py
```

### 3. Sync initial data

```bash
# Quick sync (stock list + quotes + incremental kline)
python scripts/sync_data.py

# Full sync including market special data
python scripts/sync_data.py --full
```

### 4. Start the services

```bash
# Terminal 1: Start API server
cd backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start MCP server (optional, for AI tool integration)
python -m mcp_server.server --transport http --port 8001

# Terminal 3: Start frontend
cd frontend
npm run dev
```

### 5. Access the app

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc
- **MCP Server**: http://localhost:8001/sse

---

## 🤖 MCP Integration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "command": "python",
      "args": ["-m", "mcp_server.server", "--transport", "stdio"],
      "cwd": "/path/to/financial-ai-agent/backend"
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "command": "python",
      "args": ["-m", "mcp_server.server", "--transport", "stdio"],
      "cwd": "${workspaceFolder}/backend"
    }
  }
}
```

### Windsurf

Configure in Windsurf settings with the same command and args.

### Available MCP Tools (30+)

| Category | Tools |
|----------|-------|
| **Quotes** | `get_stock_price`, `get_stock_prices_batch`, `search_stocks` |
| **K-Line** | `get_kline`, `get_kline_with_indicators` |
| **Financials** | `get_financials`, `get_financial_summary` |
| **Valuation** | `get_valuation`, `get_valuation_batch` |
| **Risk** | `analyze_risk`, `compare_risk` |
| **Market** | `get_market_overview`, `get_limit_up_pool`, `get_continuous_limit_up`, `get_hot_stocks`, `get_dragon_tiger` |
| **Index** | `get_index_quotes`, `get_index_kline` |
| **Funds** | `get_fund_nav`, `get_etf_market` |
| **Peers** | `get_peer_comparison`, `get_industry_stocks` |
| **Reference** | `get_trade_calendar`, `get_db_statistics` |

---

## 📡 API Reference

### Stock Data

| Endpoint | Description |
|----------|-------------|
| `GET /api/stocks/search?q={query}` | Search stocks by name/code |
| `GET /api/stocks/{symbol}/quote` | Real-time stock quote |
| `GET /api/stocks/{symbol}/kline` | K-line data with indicators |
| `GET /api/stocks/{symbol}/financials` | Financial statements |
| `GET /api/stocks/{symbol}/valuation` | PE/PB/PS/PCF analysis |
| `GET /api/stocks/{symbol}/risk?days=252` | Risk & return analysis |
| `GET /api/stocks/{symbol}/peers` | Industry peer comparison |

### Market Data

| Endpoint | Description |
|----------|-------------|
| `GET /api/market/overview` | Market statistics |
| `GET /api/market/indexes` | Major index quotes |
| `GET /api/market/limit-up` | Limit-up pool |
| `GET /api/market/hot-stocks` | Hot stocks ranking |
| `GET /api/market/dragon-tiger` | Dragon & Tiger board |

### Fund Data

| Endpoint | Description |
|----------|-------------|
| `GET /api/funds/{fund_code}/nav` | Fund NAV history |
| `GET /api/funds/etf` | ETF market quotes |

### Analysis

| Endpoint | Description |
|----------|-------------|
| `GET /api/analysis/compare?symbols={syms}&metric={type}` | Multi-stock comparison |

### AI Chat

| Endpoint | Description |
|----------|-------------|
| `POST /api/chat` | AI chat with generative UI tool calls |

### Admin

| Endpoint | Description |
|----------|-------------|
| `POST /api/admin/sync?table={name}` | Trigger data sync |
| `GET /api/admin/stats` | Database statistics |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/quotes` | Real-time quote streaming |

---

## 📂 Project Structure

```
financial-ai-agent/
├── backend/
│   ├── api/
│   │   ├── main.py                    # FastAPI server with all routes
│   │   └── routes/                    # Route modules
│   ├── data/
│   │   ├── schemas.py                 # DuckDB table definitions
│   │   ├── akshare_client.py          # AKShare data fetching (20+ methods)
│   │   ├── duckdb_manager.py          # Database CRUD operations
│   │   └── sync_service.py            # Incremental sync orchestrator
│   ├── analysis/
│   │   ├── technical.py               # MA, MACD, RSI, KDJ, Bollinger
│   │   ├── fundamental.py             # Scoring: profitability, growth, etc.
│   │   ├── risk.py                    # Sharpe, Beta, VaR, drawdown, etc.
│   │   └── valuation.py               # PE/PB/PS/PCF percentile analysis
│   ├── mcp_server/
│   │   ├── server.py                  # 30+ MCP tools
│   │   └── config.py                  # Integration configs
│   ├── Dockerfile
│   ├── Dockerfile.mcp
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Main chat page
│   │   ├── layout.tsx                 # Root layout
│   │   ├── globals.css                # Tailwind + A-share colors
│   │   └── api/chat/route.ts          # Chat API route
│   ├── components/
│   │   ├── chat/
│   │   │   ├── MessageList.tsx         # Chat message renderer
│   │   │   └── InputArea.tsx           # Chat input
│   │   ├── stocks/
│   │   │   ├── StockPriceCard.tsx      # Real-time price card
│   │   │   ├── KLineChart.tsx          # Interactive K-line chart
│   │   │   ├── StockTable.tsx          # Data table
│   │   │   └── ValuationCard.tsx      # PE/PB/PS/PCF display
│   │   ├── analysis/
│   │   │   └── RiskGauge.tsx          # Risk metrics dashboard
│   │   └── market/
│   │       ├── MarketOverview.tsx      # Market-wide statistics
│   │       ├── LimitUpPool.tsx         # Limit-up stocks
│   │       └── HotList.tsx            # Hot stocks ranking
│   ├── lib/
│   │   └── utils.ts                   # API client, formatters
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   ├── init_db.py                     # Database initialization
│   ├── sync_data.py                   # Data sync script
│   └── download_market_data.py        # Bulk market download
├── data/                              # DuckDB database files
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🎨 Generative UI

The frontend uses a **generative UI** pattern where tool invocations from the AI chat API automatically render appropriate React components:

```
User: "分析 000001 的技术面和估值"
       ↓
API returns: { toolInvocations: [
  { toolName: "showStockPrice", args: {symbol: "000001"} },
  { toolName: "showKLineChart", args: {symbol: "000001"} },
  { toolName: "showValuation", args: {symbol: "000001"} }
]}
       ↓
React renders: <StockPriceCard /> <KLineChart /> <ValuationCard />
```

### A-Share Color Convention
- 🔴 **Red = Price Up** (Chinese convention)
- 🟢 **Green = Price Down**

---

## 🔧 Data Pipeline

```bash
# Initialize database schema
python scripts/init_db.py

# Full data sync
python scripts/sync_data.py --full

# Sync specific components
python scripts/sync_data.py --stocks     # Stock list only
python scripts/sync_data.py --quotes     # Real-time quotes only
python scripts/sync_data.py --kline      # K-line incrementally
python scripts/sync_data.py --symbol 000001  # Single stock

# Download full market data for backtesting
python scripts/download_market_data.py --start 20100101

# Query local DuckDB directly
python -c "
from backend.data.duckdb_manager import DuckDBManager
db = DuckDBManager()
print(db.query('SELECT * FROM v_stock_latest LIMIT 5'))
"
```

---

## 🐳 Docker Deployment

```bash
# Build and run all services
docker-compose up -d

# Or build individually
docker build -t finance-backend -f backend/Dockerfile backend/
docker build -t finance-mcp -f backend/Dockerfile.mcp backend/
docker build -t finance-frontend -f frontend/Dockerfile frontend/
```

---

## 📊 Data Sources

- **AKShare** — Primary data source for A-share market data (free, no registration)
- **DuckDB** — Local analytics database with SQL interface
- **Parquet** — Export format for backtesting and sharing

---

## ⚠️ Disclaimer

This project is for **educational and research purposes only**. It does not constitute financial advice. Always consult with a licensed financial advisor before making investment decisions. Past performance does not guarantee future results.

---

## 📝 License

MIT License — see LICENSE file for details.

---

## 🤝 Contributing

Contributions welcome! Please open issues or PRs for:
- New data sources (Tushare, Wind, etc.)
- Additional technical indicators
- LLM integration (Claude, GPT, Gemini)
- Bug fixes and performance improvements
