/**
 * InputArea component - chat input with submit and loading states.
 */

"use client";

import React, { useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export function InputArea({
  value,
  onChange,
  onSubmit,
  isLoading,
  placeholder = "输入股票代码或提问...",
}: InputAreaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    if (value.trim() && !isLoading) {
      onSubmit(value.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-3 bg-card border rounded-xl p-3 shadow-sm">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        disabled={isLoading}
        className="flex-1 resize-none bg-transparent px-2 py-1 text-sm focus:outline-none disabled:opacity-50 placeholder:text-muted-foreground"
      />

      <button
        onClick={handleSubmit}
        disabled={!value.trim() || isLoading}
        className={cn(
          "flex-shrink-0 p-2 rounded-lg transition-colors",
          value.trim() && !isLoading
            ? "bg-primary text-primary-foreground hover:bg-primary/90"
            : "bg-muted text-muted-foreground cursor-not-allowed"
        )}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Send className="w-5 h-5" />
        )}
      </button>
    </div>
  );
}
