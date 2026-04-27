"use client";

import { FormEvent, useState } from "react";
import { BotMessageSquare, Database, Loader2, Send, Sparkles, UserRound } from "lucide-react";

import { api } from "@/lib/api";
import type {
  AISearchResponse,
  CategorySummary,
  RepoBriefResponse,
  TopicRotation,
  TrendingRepo,
} from "@/lib/types";
import { formatNumber, truncate } from "@/lib/utils";

type ChatRole = "assistant" | "user";

interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  sources?: string[];
}

interface AnswerContext {
  categories: CategorySummary[];
  repoBrief: RepoBriefResponse | null;
  search: AISearchResponse | null;
  topics: TopicRotation[];
  trending: TrendingRepo[];
}

const EXAMPLE_QUESTIONS = [
  "Repo nao dang tang sao nhanh nhat trong 7 ngay?",
  "Chu de nao dang xoay nhanh nhat?",
  "Tim cac repo ve browser automation agents",
  "Phan tich microsoft/autogen",
];

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function extractRepoName(question: string): string | null {
  const match = question.match(/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+/);
  return match?.[0] ?? null;
}

function isCategoryQuestion(question: string): boolean {
  return /category|categories|danh muc|nhom|phan khuc|segment/i.test(question);
}

function isTopicQuestion(question: string): boolean {
  return /topic|topics|tag|tags|chu de|cong nghe|stack/i.test(question);
}

function isBriefQuestion(question: string): boolean {
  return /brief|summary|summarize|tom tat|phan tich|vi sao|why/i.test(question);
}

function formatTrendingRepos(repos: TrendingRepo[]): string {
  if (repos.length === 0) {
    return "Chua co repo nao vuot nguong trending trong cua so hien tai.";
  }

  return repos
    .slice(0, 5)
    .map(
      (item, index) =>
        `${index + 1}. ${item.repo.repo_full_name}: +${formatNumber(
          item.star_count_in_window,
        )} stars, ${item.repo.primary_language || "Unknown"} / ${item.repo.category}`,
    )
    .join("\n");
}

function formatTopicRotation(topics: TopicRotation[]): string {
  if (topics.length === 0) {
    return "Chua co topic nao du du lieu de xep hang rotation.";
  }

  return topics
    .slice(0, 6)
    .map(
      (topic, index) =>
        `${index + 1}. ${topic.topic}: +${formatNumber(topic.star_delta)} stars tren ${formatNumber(
          topic.repo_count,
        )} repos`,
    )
    .join("\n");
}

function formatCategorySummary(categories: CategorySummary[]): string {
  if (categories.length === 0) {
    return "Chua co category summary tu backend.";
  }

  return [...categories]
    .sort((left, right) => right.weekly_star_delta - left.weekly_star_delta)
    .slice(0, 6)
    .map(
      (item, index) =>
        `${index + 1}. ${item.category}: ${formatNumber(item.repo_count)} repos, ${formatNumber(
          item.total_stars,
        )} stars, weekly delta +${formatNumber(item.weekly_star_delta)}`,
    )
    .join("\n");
}

function formatSearchResults(search: AISearchResponse | null): string {
  if (!search || search.results.length === 0) {
    return "Khong tim thay repo nao khop manh voi cau hoi nay.";
  }

  return search.results
    .slice(0, 5)
    .map((result, index) => {
      const description = result.repo.description
        ? ` - ${truncate(result.repo.description, 96)}`
        : "";
      return `${index + 1}. ${result.repo.repo_full_name}: score ${result.score.toFixed(
        2,
      )}, +${formatNumber(result.star_count_in_window)} stars${description}`;
    })
    .join("\n");
}

function composeAnswer(question: string, context: AnswerContext): string {
  const repoName = extractRepoName(question);

  if (repoName && context.repoBrief) {
    return [
      `Phan tich nhanh ${context.repoBrief.repo.repo_full_name}`,
      "",
      context.repoBrief.headline,
      context.repoBrief.summary,
      "",
      `Vi sao dang dang chu y: ${context.repoBrief.why_trending}`,
      "",
      `Tin hieu dinh luong: +${formatNumber(
        context.repoBrief.star_count_in_window,
      )} stars, ${formatNumber(
        context.repoBrief.total_events_in_window,
      )} events, ${formatNumber(context.repoBrief.unique_actors_in_window)} actors trong ${
        context.repoBrief.window_days
      } ngay.`,
      "",
      `Watchouts: ${context.repoBrief.watchouts.join("; ") || "Chua co watchout noi bat."}`,
    ].join("\n");
  }

  if (isCategoryQuestion(question)) {
    return [
      "Cac category dang co chuyen dong manh nhat:",
      "",
      formatCategorySummary(context.categories),
      "",
      "Doc nhanh: category co weekly delta cao thuong dang co demand moi; category co tong sao cao nhung delta thap la nhom truong thanh hon.",
    ].join("\n");
  }

  if (isTopicQuestion(question)) {
    return [
      "Cac topic dang rotate nhanh nhat:",
      "",
      formatTopicRotation(context.topics),
      "",
      "Day la danh sach so sanh voi cua so truoc do, nen no hop de bat breakout som hon bang tong sao tuyet doi.",
    ].join("\n");
  }

  if (isBriefQuestion(question)) {
    return [
      "Tom tat nhanh tu data hien co:",
      "",
      "Repos dang co momentum:",
      formatTrendingRepos(context.trending),
      "",
      "Topic rotation:",
      formatTopicRotation(context.topics),
      "",
      "Repo khop voi cau hoi:",
      formatSearchResults(context.search),
    ].join("\n");
  }

  return [
    "Mình đọc câu hỏi theo hướng truy vấn GitHub AI market data. Đây là snapshot phù hợp nhất:",
    "",
    "Repos dang tang nhanh:",
    formatTrendingRepos(context.trending),
    "",
    "Topic dang nong:",
    formatTopicRotation(context.topics),
    "",
    "Repo khop semantic/lexical voi cau hoi:",
    formatSearchResults(context.search),
  ].join("\n");
}

async function answerQuestion(question: string): Promise<{ content: string; sources: string[] }> {
  const repoName = extractRepoName(question);

  const [categories, trending, topics, search, repoBrief] = await Promise.allSettled([
    api.getCategorySummary(),
    api.getTrending(7, 10),
    api.getTopicRotation(7, 8),
    api.getAISearch({ query: question, days: 30, minStars: 500, limit: 5 }),
    repoName ? api.getRepoBrief(repoName, 30) : Promise.resolve(null),
  ]);

  const context: AnswerContext = {
    categories: categories.status === "fulfilled" ? categories.value : [],
    trending: trending.status === "fulfilled" ? trending.value : [],
    topics: topics.status === "fulfilled" ? topics.value : [],
    search: search.status === "fulfilled" ? search.value : null,
    repoBrief: repoBrief.status === "fulfilled" ? repoBrief.value : null,
  };

  const loadedAnything =
    context.categories.length > 0 ||
    context.trending.length > 0 ||
    context.topics.length > 0 ||
    context.search !== null ||
    context.repoBrief !== null;

  if (!loadedAnything) {
    throw new Error("No GitHub trend data endpoints returned data.");
  }

  return {
    content: composeAnswer(question, context),
    sources: [
      "/dashboard/category-summary",
      "/dashboard/trending",
      "/dashboard/topic-rotation",
      "/ai/search",
      ...(repoName ? ["/ai/repo-brief"] : []),
    ],
  };
}

export function GitHubDataChatbot() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createId(),
      role: "assistant",
      content:
        "Hoi minh ve GitHub AI trend data: repo nao dang tang nhanh, topic nao dang hot, category nao dang dich chuyen, hoac nhap owner/repo de lay repo brief.",
      sources: ["/dashboard/*", "/ai/*"],
    },
  ]);

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const question = input.trim();
    if (question.length < 2 || isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: question,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const answer = await answerQuestion(question);
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: answer.content,
          sources: answer.sources,
        },
      ]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown chatbot error.";
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: `Minh chua lay duoc data de tra loi cau nay.\n\nChi tiet: ${detail}`,
          sources: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function fillExample(question: string) {
    setInput(question);
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="card-glow flex min-h-[660px] flex-col overflow-hidden rounded-lg border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-sky-500/10 via-emerald-500/10 to-amber-500/10 px-4 py-4 sm:px-5">
          <div className="flex items-center gap-2">
            <BotMessageSquare className="h-5 w-5 text-sky-500" />
            <div>
              <h2 className="text-sm font-semibold">GitHub Data Chatbot</h2>
              <p className="text-xs text-muted-foreground">
                Grounded on dashboard and AI endpoints
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/78 px-3 py-1.5 text-xs text-slate-600 sm:flex">
            <Database className="h-3.5 w-3.5" />
            Live data
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
          {messages.map((message) => {
            const isAssistant = message.role === "assistant";
            const Icon = isAssistant ? Sparkles : UserRound;

            return (
              <div
                key={message.id}
                className={`flex gap-3 ${isAssistant ? "justify-start" : "justify-end"}`}
              >
                {isAssistant && (
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sky-600">
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
                  <div className="whitespace-pre-wrap">{message.content}</div>
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
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-sky-500 bg-sky-600 text-white">
                    <Icon className="h-4 w-4" />
                  </span>
                )}
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Querying GitHub trend data...
            </div>
          )}
        </div>

        <form onSubmit={submitQuestion} className="border-t border-border p-4 sm:p-5">
          <div className="flex flex-col gap-3 lg:flex-row">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask: Which repos are breaking out in AI agents?"
              className="min-h-11 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-sky-400"
            />
            <button
              type="submit"
              disabled={input.trim().length < 2 || isLoading}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Ask
            </button>
          </div>
        </form>
      </div>

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
        <div className="mt-6 rounded-lg border border-slate-200 bg-white/82 p-4">
          <div className="text-sm font-semibold text-slate-950">Grounding model</div>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The chatbot answers from existing API data and shows the endpoints it used.
            When you include an owner/repo name, it also pulls the repo brief endpoint.
          </p>
        </div>
      </aside>
    </section>
  );
}
