/**
 * Chat API Route
 * Proxies requests to the Python backend or handles them directly.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Invalid request: messages array required" },
        { status: 400 }
      );
    }

    // Limit message count to prevent abuse
    if (messages.length > 100) {
      return NextResponse.json(
        { error: "Too many messages" },
        { status: 400 }
      );
    }

    // Get the last user message
    const lastUserMessage = [...messages].reverse().find((m) => m.role === "user");

    if (!lastUserMessage) {
      return NextResponse.json(
        { content: "请提出您的金融分析问题。" }
      );
    }

    // Sanitize and truncate content
    let content = String(lastUserMessage.content || "").trim();
    if (content.length > 2000) {
      content = content.substring(0, 2000);
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // Parse intent and determine tool invocations
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    const toolInvocations: any[] = [];

    // Detect stock symbols (6-digit codes)
    const symbols = content.match(/\b(\d{6})\b/g) || [];

    // --- Market Overview ---
    if (
      content.includes("市场总览") ||
      content.includes("大盘") ||
      content.includes("市场概况") ||
      content.includes("今日市场")
    ) {
      toolInvocations.push({
        toolName: "showMarketOverview",
        args: {},
        state: "completed",
        result: await fetchMarketOverview(),
      });
    }

    // --- Hot Stocks ---
    if (
      content.includes("热门") ||
      content.includes("热榜") ||
      content.includes("热度") ||
      content.includes("关注度")
    ) {
      toolInvocations.push({
        toolName: "showHotList",
        args: {},
        state: "completed",
        result: await fetchHotStocks(),
      });
    }

    // --- Limit-Up Pool ---
    if (
      content.includes("涨停") ||
      content.includes("涨停池") ||
      content.includes("涨停板") ||
      content.includes("打板")
    ) {
      toolInvocations.push({
        toolName: "showLimitUpPool",
        args: {},
        state: "completed",
        result: await fetchLimitUpPool(),
      });
    }

    // --- Stock-specific analysis ---
    for (const symbol of symbols) {
      // Stock price card
      if (
        content.includes("行情") ||
        content.includes("价格") ||
        content.includes("查询") ||
        content.includes("最新价") ||
        content.includes("涨跌") ||
        content.includes(symbol)
      ) {
        try {
          const quoteData = await fetchStockQuote(symbol);
          toolInvocations.push({
            toolName: "showStockPrice",
            args: { symbol },
            state: "completed",
            result: quoteData,
          });
        } catch (e) {
          // Skip if quote fails
        }
      }

      // K-line chart
      if (
        content.includes("K线") ||
        content.includes("走势") ||
        content.includes("图表") ||
        content.includes("技术分析") ||
        content.includes("趋势") ||
        content.includes("MACD") ||
        content.includes("均线") ||
        content.includes("分析")
      ) {
        try {
          const klineData = await fetchStockKline(symbol);
          toolInvocations.push({
            toolName: "showKLineChart",
            args: { symbol },
            state: "completed",
            result: klineData,
          });
        } catch (e) {
          // Skip if kline fails
        }
      }

      // Valuation
      if (
        content.includes("估值") ||
        content.includes("PE") ||
        content.includes("PB") ||
        content.includes("市盈率") ||
        content.includes("市净率") ||
        content.includes("低估") ||
        content.includes("高估")
      ) {
        try {
          const valData = await fetchStockValuation(symbol);
          toolInvocations.push({
            toolName: "showValuation",
            args: { symbol },
            state: "completed",
            result: valData,
          });
        } catch (e) {
          // Skip
        }
      }

      // Risk analysis
      if (
        content.includes("风险") ||
        content.includes("波动") ||
        content.includes("回撤") ||
        content.includes("夏普") ||
        content.includes("VaR") ||
        content.includes("回报率") ||
        content.includes("收益率")
      ) {
        try {
          const riskData = await fetchStockRisk(symbol);
          toolInvocations.push({
            toolName: "showRiskAnalysis",
            args: { symbol },
            state: "completed",
            result: riskData,
          });
        } catch (e) {
          // Skip
        }
      }
    }

    // --- Index data ---
    if (
      content.includes("指数") ||
      content.includes("沪深300") ||
      content.includes("上证") ||
      content.includes("创业板") ||
      content.includes("科创")
    ) {
      try {
        const indexData = await fetchIndexes();
        toolInvocations.push({
          toolName: "showStockTable",
          args: { title: "主要指数行情" },
          state: "completed",
          result: indexData,
        });
      } catch (e) {
        // Skip
      }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // Generate response text
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    let responseText = "";

    if (toolInvocations.length === 0) {
      responseText = `🔍 **金融AI助手**

我理解您的问题："${content.substring(0, 100)}${content.length > 100 ? "..." : ""}"

💡 **您可以尝试以下操作：**
- 📊 输入 **"市场总览"** 查看今日A股市场概况
- 🔥 输入 **"热门股票"** 查看市场关注度排行
- 📈 输入 **"涨停池"** 查看今日涨停板
- 💹 输入股票代码 + **"分析"** 获取综合分析（如 "分析 000001"）
- ⚠️ 输入股票代码 + **"风险"** 评估投资风险（如 "风险 600519"）
- 📋 输入股票代码 + **"估值"** 查看PE/PB估值（如 "估值 300750"）
- 🏦 输入 **"指数"** 查看主要指数行情

请直接输入指令，我将为您调取实时数据！`;
    } else {
      const toolNames = toolInvocations.map((t) => {
        const nameMap: Record<string, string> = {
          showStockPrice: "📊 实时行情",
          showKLineChart: "📈 K线走势",
          showValuation: "💰 估值分析",
          showRiskAnalysis: "⚠️ 风险评估",
          showMarketOverview: "🏛️ 市场总览",
          showLimitUpPool: "🚀 涨停池",
          showHotList: "🔥 热榜",
          showStockTable: "📋 数据表格",
        };
        return nameMap[t.toolName] || t.toolName;
      });

      responseText = `✅ 已为您加载以下数据：\n\n${toolNames.map((n) => `- ${n}`).join("\n")}\n\n请查看下方生成的数据卡片：`;
    }

    return NextResponse.json({
      role: "assistant",
      content: responseText,
      toolInvocations,
    });
  } catch (error: any) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      { error: "Chat processing failed", detail: error.message },
      { status: 500 }
    );
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Data fetching helpers (server-side, with timeout)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const FETCH_TIMEOUT_MS = 15000; // 15 second timeout

async function fetchWithTimeout(url: string): Promise<any> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchStockQuote(symbol: string) {
  return fetchWithTimeout(`${BACKEND_URL}/api/stocks/${symbol}/quote`);
}

async function fetchStockKline(symbol: string) {
  return fetchWithTimeout(
    `${BACKEND_URL}/api/stocks/${symbol}/kline?limit=120&with_indicators=true`
  );
}

async function fetchStockValuation(symbol: string) {
  return fetchWithTimeout(`${BACKEND_URL}/api/stocks/${symbol}/valuation`);
}

async function fetchStockRisk(symbol: string) {
  return fetchWithTimeout(`${BACKEND_URL}/api/stocks/${symbol}/risk?days=252`);
}

async function fetchMarketOverview() {
  return fetchWithTimeout(`${BACKEND_URL}/api/market/overview`);
}

async function fetchHotStocks() {
  return fetchWithTimeout(`${BACKEND_URL}/api/market/hot-stocks`);
}

async function fetchLimitUpPool() {
  return fetchWithTimeout(`${BACKEND_URL}/api/market/limit-up`);
}

async function fetchIndexes() {
  return fetchWithTimeout(`${BACKEND_URL}/api/market/indexes`);
}
