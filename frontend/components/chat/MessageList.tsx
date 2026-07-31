/**
 * MessageList component - renders chat messages with embedded tool results.
 */

"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Bot, User, AlertCircle } from "lucide-react";

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

interface MessageListProps {
  messages: Message[];
  toolComponents: Record<string, React.ComponentType<any>>;
}

export function MessageList({ messages, toolComponents }: MessageListProps) {
  return (
    <div className="space-y-6">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn(
            "animate-fade-in",
            msg.role === "user" ? "flex justify-end" : "flex gap-3"
          )}
        >
          {/* User message bubble */}
          {msg.role === "user" && (
            <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-br-md bg-primary text-primary-foreground">
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          )}

          {/* Assistant message */}
          {msg.role === "assistant" && (
            <div className="flex gap-3 w-full">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1 space-y-3 min-w-0">
                {/* Text content */}
                {msg.content && (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <div
                      dangerouslySetInnerHTML={{
                        __html: formatMarkdown(msg.content),
                      }}
                    />
                  </div>
                )}

                {/* Tool results as generative UI */}
                {msg.toolInvocations?.map((invocation, idx) => {
                  const Component = toolComponents[invocation.toolName];
                  if (!Component) return null;

                  return (
                    <div key={idx} className="genui-card animate-slide-up">
                      {invocation.state === "pending" && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                          加载中...
                        </div>
                      )}
                      {invocation.state === "completed" && (
                        <Component
                          {...invocation.args}
                          data={invocation.result}
                        />
                      )}
                      {invocation.state === "error" && (
                        <div className="text-destructive text-sm">
                          数据加载失败
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* System message */}
          {msg.role === "system" && (
            <div className="flex gap-3 w-full">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="prose prose-sm dark:prose-invert text-muted-foreground">
                <div
                  dangerouslySetInnerHTML={{
                    __html: formatMarkdown(msg.content),
                  }}
                />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/** Simple markdown formatting with XSS protection */
function formatMarkdown(text: string): string {
  // First: escape any existing HTML to prevent XSS
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");

  // Then: apply safe markdown transformations on the escaped text
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+?)`/g, "<code class='bg-muted px-1 rounded text-sm'>$1</code>")
    .replace(/\n/g, "<br/>")
    .replace(
      /^- (.+)$/gm,
      '<li style="margin-left:1rem;list-style:disc">$1</li>'
    );
}
