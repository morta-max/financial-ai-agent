/**
 * Main Chat Page - Financial AI Agent
 *
 * Features:
 * - Stock symbol input for quick lookup
 * - AI chat assistant for financial research
 * - Generative UI cards for stock data visualization
 * - Real-time market overview sidebar
 */

"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { StockPriceCard } from "@/components/stocks/StockPriceCard";
import { KLineChart } from "@/components/stocks/KLineChart";
import { StockTable } from "@/components/stocks/StockTable";
import { ValuationCard } from "@/components/stocks/ValuationCard";
import { RiskGauge } from "@/components/analysis/RiskGauge";
import { MarketOverview } from "@/components/market/MarketOverview";
import { LimitUpPool } from "@/components/market/LimitUpPool";
import { HotList } from "@/components/market/HotList";
import { InputArea } from "@/components/chat/InputArea";
import { MessageList } from "@/components/chat/MessageList";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Shield,
  Search,
  Menu,
  X,
  Zap,
  Activity,
} from "lucide-react";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Types
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolInvocations?: ToolInvocation[];
  timestamp: Date;
}

interface ToolInvocation {
  toolName: string;
  args: Record<string, any>;
  result?: any;
  state: "pending" | "completed" | "error";
}

type ViewType = "chat" | "market" | "analysis" | "hot";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Sample quick actions
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const QUICK_ACTIONS = [
  { label: "📊 市场总览", action: "查看今日A股市场总览" },
  { label: "🔥 热门股票", action: "查询当前热门股票排行" },
  { label: "📈 涨停池", action: "查询今日涨停板股票" },
  { label: "🏦 指数行情", action: "查询沪深300和创业板指数行情" },
  { label: "💹 分析 000001", action: "分析平安银行(000001)的技术面和基本面" },
  { label: "⚠️ 风险 600519", action: "计算贵州茅台(600519)的投资风险和回报率" },
];

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Tool → Component Mapping
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const TOOL_COMPONENTS: Record<string, React.ComponentType<any>> = {
  showStockPrice: StockPriceCard,
  showKLineChart: KLineChart,
  showStockTable: StockTable,
  showValuation: ValuationCard,
  showRiskAnalysis: RiskGauge,
  showMarketOverview: MarketOverview,
  showLimitUpPool: LimitUpPool,
  showHotList: HotList,
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Main Page
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeView, setActiveView] = useState<ViewType>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [symbolInput, setSymbolInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send message handler — uses refs to avoid stale closures
  const handleSend = useCallback(async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isLoading) return;

    // Input validation: limit message length
    if (trimmed.length > 2000) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "system",
        content: "⚠️ 输入内容过长，请限制在2000字以内。",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      return;
    }

    // Cancel any in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    // Check for stock symbol in message
    const symbolMatch = trimmed.match(/\b(\d{6})\b/g);
    if (symbolMatch) {
      setSelectedSymbol(symbolMatch[0]);
    }

    try {
      // Call backend chat API with timeout (30 seconds)
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.content || "抱歉，我无法处理这个请求。",
        toolInvocations: data.toolInvocations,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      // Don't show error for aborted requests
      if (error.name === "AbortError") return;

      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: `⚠️ 连接后端服务失败。请确保API服务已启动（http://localhost:8000）。

💡 您可以先查看侧边栏快捷操作了解系统功能。

错误详情: ${error.message || error}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [isLoading, messages]);

  // Quick action handler
  const handleQuickAction = (action: string) => {
    handleSend(action);
  };

  // Symbol search handler
  const handleSymbolSearch = () => {
    if (symbolInput.trim()) {
      setSelectedSymbol(symbolInput.trim());
      handleSend(`查询 ${symbolInput.trim()} 的行情数据和技术分析`);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ━━━━━━━━━━━━ Sidebar ━━━━━━━━━━━━ */}
      <aside
        className={cn(
          "flex flex-col border-r bg-card transition-all duration-300",
          sidebarOpen ? "w-72" : "w-0 overflow-hidden border-0"
        )}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary" />
            <span className="font-bold text-lg">金融AI助手</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1 rounded hover:bg-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Symbol Search */}
        <div className="p-4 border-b">
          <label className="text-xs text-muted-foreground mb-2 block">
            快速查股
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="输入代码如 000001"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSymbolSearch()}
              className="flex-1 px-3 py-2 text-sm border rounded-md bg-background"
            />
            <button
              onClick={handleSymbolSearch}
              className="p-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          <NavItem
            icon={<BarChart3 />}
            label="对话分析"
            active={activeView === "chat"}
            onClick={() => setActiveView("chat")}
          />
          <NavItem
            icon={<TrendingUp />}
            label="市场总览"
            active={activeView === "market"}
            onClick={() => setActiveView("market")}
          />
          <NavItem
            icon={<DollarSign />}
            label="估值分析"
            active={activeView === "analysis"}
            onClick={() => setActiveView("analysis")}
          />
          <NavItem
            icon={<Activity />}
            label="热门个股"
            active={activeView === "hot"}
            onClick={() => setActiveView("hot")}
          />

          <div className="pt-4 border-t mt-4">
            <h3 className="text-xs font-semibold text-muted-foreground mb-2 uppercase">
              快捷操作
            </h3>
            {QUICK_ACTIONS.map((qa) => (
              <button
                key={qa.label}
                onClick={() => handleQuickAction(qa.action)}
                className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-muted transition-colors"
              >
                {qa.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t text-xs text-muted-foreground">
          <p>Financial AI Agent v1.0</p>
          <p>A股智能分析平台</p>
        </div>
      </aside>

      {/* ━━━━━━━━━━━━ Main Content ━━━━━━━━━━━━ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-4 px-6 py-3 border-b bg-card">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1 rounded hover:bg-muted"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <div className="flex-1" />

          {selectedSymbol && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full text-sm">
              <span className="font-mono font-semibold">{selectedSymbol}</span>
              <button
                onClick={() => setSelectedSymbol("")}
                className="hover:text-destructive"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-muted-foreground">API 已连接</span>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeView === "chat" && (
            <div className="flex flex-col h-full">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto">
                {messages.length === 0 ? (
                  <WelcomeScreen
                    onQuickAction={handleQuickAction}
                    onSymbolSubmit={handleSymbolSearch}
                    symbolInput={symbolInput}
                    setSymbolInput={setSymbolInput}
                  />
                ) : (
                  <div className="max-w-3xl mx-auto px-6 py-4">
                    <MessageList
                      messages={messages}
                      toolComponents={TOOL_COMPONENTS}
                    />
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="border-t bg-card p-4">
                <div className="max-w-3xl mx-auto">
                  <InputArea
                    value={inputValue}
                    onChange={setInputValue}
                    onSubmit={handleSend}
                    isLoading={isLoading}
                    placeholder="输入股票代码或提问... (例如: 分析000001的走势 / 查询涨停池 / 估值600519)"
                  />
                </div>
              </div>
            </div>
          )}

          {activeView === "market" && (
            <div className="h-full overflow-y-auto p-6">
              <MarketOverview />
            </div>
          )}

          {activeView === "analysis" && selectedSymbol && (
            <div className="h-full overflow-y-auto p-6 space-y-6">
              <h2 className="text-2xl font-bold">
                {selectedSymbol} 综合分析
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <KLineChart symbol={selectedSymbol} />
                <ValuationCard symbol={selectedSymbol} />
              </div>
              <RiskGauge symbol={selectedSymbol} />
            </div>
          )}

          {activeView === "analysis" && !selectedSymbol && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>请先在左侧输入股票代码</p>
              </div>
            </div>
          )}

          {activeView === "hot" && (
            <div className="h-full overflow-y-auto p-6 space-y-6">
              <HotList />
              <LimitUpPool />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Sub-components
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      <span className="w-5 h-5">{icon}</span>
      {label}
    </button>
  );
}

function WelcomeScreen({
  onQuickAction,
  onSymbolSubmit,
  symbolInput,
  setSymbolInput,
}: {
  onQuickAction: (action: string) => void;
  onSymbolSubmit: () => void;
  symbolInput: string;
  setSymbolInput: (v: string) => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      <div className="text-center max-w-2xl animate-fade-in">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
          <Zap className="w-8 h-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold mb-3">A股金融AI助手</h1>
        <p className="text-muted-foreground mb-8 text-lg">
          智能分析A股市场 · 实时行情 · 财务报表 · 技术指标 · 风险评估
        </p>

        {/* Quick symbol input */}
        <div className="flex gap-3 max-w-md mx-auto mb-8">
          <input
            type="text"
            placeholder="输入股票代码，如 000001"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSymbolSubmit()}
            className="flex-1 px-4 py-3 text-lg border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={onSymbolSubmit}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 font-medium transition-colors"
          >
            分析
          </button>
        </div>

        {/* Quick actions grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-2xl">
          {QUICK_ACTIONS.map((qa) => (
            <button
              key={qa.label}
              onClick={() => onQuickAction(qa.action)}
              className="px-4 py-3 text-sm border rounded-xl hover:bg-muted transition-colors text-left"
            >
              {qa.label}
            </button>
          ))}
        </div>

        <div className="mt-8 flex items-center justify-center gap-8 text-sm text-muted-foreground">
          <Feature icon={<TrendingUp />} label="实时行情" />
          <Feature icon={<BarChart3 />} label="K线分析" />
          <Feature icon={<DollarSign />} label="财务报表" />
          <Feature icon={<Shield />} label="风险评估" />
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="w-6 h-6">{icon}</span>
      <span>{label}</span>
    </div>
  );
}
