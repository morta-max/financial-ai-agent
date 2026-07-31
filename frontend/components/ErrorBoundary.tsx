/**
 * Error Boundary component to catch rendering errors from tool components.
 * Prevents the entire page from crashing when a single component fails.
 */

"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-6 border border-destructive/30 rounded-xl bg-destructive/5 text-center">
          <AlertTriangle className="w-8 h-8 mx-auto mb-3 text-destructive/70" />
          <h3 className="font-semibold mb-1">组件渲染失败</h3>
          <p className="text-sm text-muted-foreground mb-3">
            {this.state.error?.message || "未知错误"}
          </p>
          <button
            onClick={this.handleRetry}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-muted hover:bg-muted/80 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            重试
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
