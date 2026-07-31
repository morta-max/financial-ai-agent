import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "A-Share Financial AI Agent",
  description: "AI-powered financial research and stock analysis platform for A-shares. Real-time quotes, K-line charts, financial statements, valuation analysis, risk assessment, and more.",
  keywords: ["A股", "股票分析", "AI金融", "财务分析", "技术分析", "估值", "风险评估"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-background antialiased">
        {children}
      </body>
    </html>
  );
}
