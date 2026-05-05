"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { BotMessageSquare, Database, Loader2, Send, Sparkles, UserRound } from "lucide-react";

import { api } from "@/lib/api";
import type { AIChatEvidence, AIChatMessage } from "@/lib/types";

type ChatRole = "assistant" | "user";

interface ChatThreadMessage {
  id: string;
  role: ChatRole;
  content: string;
  intent?: string;
  sources?: string[];
  evidence?: AIChatEvidence[];
}

const EXAMPLE_QUESTIONS = [
  "Repo nao dang tang sao nhanh nhat trong 7 ngay?",
  "Chu de nao dang xoay nhanh nhat?",
  "Tim cac repo ve browser automation agents",
  "Phan tich microsoft/autogen",
];

const INTENT_LABELS: Record<string, string> = {
  instant: "Instant",
  search: "Search",
  knowledge: "Knowledge",
  market: "Knowledge",
  repo: "Knowledge",
  mixed: "Knowledge",
};

const INTENT_COLORS: Record<string, string> = {
  instant: "bg-violet-50 border-violet-200 text-violet-600",
  search: "bg-amber-50 border-amber-200 text-amber-600",
  knowledge: "bg-emerald-50 border-emerald-200 text-emerald-600",
  market: "bg-emerald-50 border-emerald-200 text-emerald-600",
  repo: "bg-emerald-50 border-emerald-200 text-emerald-600",
  mixed: "bg-slate-50 border-slate-200 text-slate-600",
};

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function toApiHistory(messages: ChatThreadMessage[]): AIChatMessage[] {
  return messages.slice(-8).map((message) => ({
    role: message.role,
    content: message.content,
  }));
}

export function GitHubDataChatbot() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatThreadMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const question = input.trim();
    if (question.length < 2 || isLoading) {
      return;
    }

    const userMessage: ChatThreadMessage = {
      id: createId(),
      role: "user",
      content: question,
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.chatWithGithubData({
        question,
        days: 30,
        history: toApiHistory(messages),
      });
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: response.answer,
          intent: response.intent,
          sources: response.tools_used.map((tool) => `/ai/${tool}`),
          evidence: response.evidence,
        },
      ]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error.";
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: `Minh chua lay duoc data de tra loi cau nay.\n\nChi tiet: ${detail}`,
          sources: ["/ai/chat"],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function fillExample(question: string) {
    setInput(question);
  }

  const isEmpty = messages.length === 0;

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="card-glow flex min-h-[660px] flex-col overflow-hidden rounded-lg border border-border bg-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-sky-500/10 via-emerald-500/10 to-amber-500/10 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-2">
            <BotMessageSquare className="h-5 w-5 text-sky-500" />
            <span className="text-sm font-semibold">GitHub AI Agent</span>
          </div>
          <div className="hidden items-center gap-1.5 rounded-full border border-slate-200 bg-white/78 px-3 py-1 text-xs text-slate-500 sm:flex">
            <Database className="h-3 w-3" />
            grounded
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {isEmpty ? (
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <BotMessageSquare className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-muted-foreground">
                Hoi bat ky dieu gi ve GitHub trend data
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => {
                const isAssistant = message.role === "assistant";
                const Icon = isAssistant ? Sparkles : UserRound;

                return (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${isAssistant ? "justify-start" : "justify-end"}`}
                  >
                    {isAssistant && (
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sky-600">
                        <Icon className="h-4 w-4" />
                      </span>
                    )}
                    <div
                      className={`max-w-[850px] rounded-lg border px-4 py-3 text-sm leading-6 ${
                        isAssistant
                          ? "border-slate-200 bg-white text-slate-700"
                          : "border-sky-500 bg-sky-600 text-white"
                      }`}
                    >
                      {isAssistant && message.intent && (
                        <div className="mb-2">
                          <span
                            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                              INTENT_COLORS[message.intent] ?? INTENT_COLORS.mixed
                            }`}
                          >
                            {INTENT_LABELS[message.intent] ?? message.intent}
                          </span>
                        </div>
                      )}

                      <div className="whitespace-pre-wrap">{message.content}</div>

                      {message.evidence && message.evidence.length > 0 && (
                        <div className="mt-3 grid gap-2">
                          {message.evidence.slice(0, 4).map((item) => (
                            <div
                              key={`${message.id}-${item.source}-${item.label}`}
                              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
                            >
                              <div className="font-medium text-slate-950">{item.label}</div>
                              <div className="mt-1">{item.value}</div>
                              <div className="mt-1 text-slate-400">{item.source}</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.sources && message.sources.length > 0 && (
                        <div
                          className={`mt-3 flex flex-wrap gap-1.5 text-[11px] ${
                            isAssistant ? "text-slate-500" : "text-sky-100"
                          }`}
                        >
                          {message.sources.map((source) => (
                            <span
                              key={`${message.id}-${source}`}
                              className={`rounded-full border px-2 py-0.5 ${
                                isAssistant
                                  ? "border-slate-200 bg-slate-50"
                                  : "border-white/30 bg-white/10"
                              }`}
                            >
                              {source}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {!isAssistant && (
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-sky-500 bg-sky-600 text-white">
                        <Icon className="h-4 w-4" />
                      </span>
                    )}
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Classifying intent and querying tools...
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <form onSubmit={submitQuestion} className="border-t border-border p-4 sm:p-5">
          <div className="flex flex-col gap-3 lg:flex-row">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Hoi ve GitHub trends, repo, topic..."
              className="min-h-11 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-sky-400"
            />
            <button
              type="submit"
              disabled={input.trim().length < 2 || isLoading}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Ask
            </button>
          </div>
        </form>
      </div>

      {/* Sidebar */}
      <aside className="terminal-panel data-grid rounded-lg p-5">
        <div className="section-kicker">Try Asking</div>
        <div className="mt-4 grid gap-2">
          {EXAMPLE_QUESTIONS.map((question) => (
            <button
              key={question}
              onClick={() => fillExample(question)}
              className="rounded-lg border border-slate-200 bg-white/82 px-4 py-3 text-left text-sm text-slate-700 transition-colors hover:bg-white hover:text-slate-950"
            >
              {question}
            </button>
          ))}
        </div>

        <div className="mt-6 grid gap-2">
          {[
            { color: "bg-violet-400", label: "Instant", desc: "Direct from LLM knowledge" },
            { color: "bg-amber-400", label: "Search", desc: "Finds matching repos" },
            { color: "bg-emerald-400", label: "Knowledge", desc: "Queries live trend data" },
          ].map(({ color, label, desc }) => (
            <div
              key={label}
              className="flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white/82 px-3 py-2.5"
            >
              <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${color}`} />
              <div>
                <div className="text-xs font-semibold text-slate-900">{label}</div>
                <div className="text-xs text-slate-500">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
