"use client";

import { startTransition, useDeferredValue, useState } from "react";
import {
  ArrowUpRight,
  BrainCircuit,
  Search,
  Sparkles,
  Star,
  TrendingUp,
} from "lucide-react";

import { useAISearch } from "@/hooks/useAISearch";
import { CATEGORY_COLORS, CATEGORY_LABELS, type Category } from "@/lib/types";
import { cn, formatNumber, truncate } from "@/lib/utils";

const EXAMPLE_QUERIES = [
  "agent frameworks for browser automation",
  "multimodal speech and audio generation",
  "vector database and retrieval infrastructure",
];

interface Props {
  category: Category;
  days: number;
  onSelectRepo: (name: string) => void;
}

export function AISearchPanel({ category, days, onSelectRepo }: Props) {
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [minStars, setMinStars] = useState(1_000);
  const deferredQuery = useDeferredValue(query.trim());
  const activeCategory = category === "all" ? undefined : category;
  const { data, error, isFetching } = useAISearch({
    query: deferredQuery,
    category: activeCategory,
    days,
    language: language.trim() || undefined,
    minStars,
    enabled: deferredQuery.length >= 2,
  });

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border bg-gradient-to-r from-sky-500/10 via-cyan-500/10 to-emerald-500/10 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <BrainCircuit className="h-4 w-4 text-cyan-400" />
              AI Discovery Search
            </div>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Search repositories by intent instead of exact keywords. The backend
              reranks candidates lexically and, when available, semantically.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            {data ? (
              <span>
                {data.retrieval_mode === "hybrid" ? "hybrid" : "lexical"} mode ·{" "}
                {data.total_candidates} candidates scanned
              </span>
            ) : (
              <span>ready for natural-language repo search</span>
            )}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_160px_140px]">
          <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try: browser-use agents for web automation"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </label>

          <input
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            placeholder="Language"
            className="rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground"
          />

          <select
            value={minStars}
            onChange={(event) => setMinStars(Number(event.target.value))}
            className="rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none"
          >
            <option value={500}>500+ stars</option>
            <option value={1_000}>1k+ stars</option>
            <option value={5_000}>5k+ stars</option>
            <option value={10_000}>10k+ stars</option>
          </select>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {EXAMPLE_QUERIES.map((example) => (
            <button
              key={example}
              onClick={() => startTransition(() => setQuery(example))}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-cyan-400/50 hover:text-foreground"
            >
              {example}
            </button>
          ))}
          {activeCategory && (
            <span
              className="rounded-full px-3 py-1 text-xs font-medium text-white"
              style={{
                backgroundColor: CATEGORY_COLORS[activeCategory] ?? "#3b82f6",
              }}
            >
              {CATEGORY_LABELS[activeCategory] ?? activeCategory}
            </span>
          )}
          <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
            window: {days}d
          </span>
        </div>
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        {deferredQuery.length < 2 && (
          <div className="rounded-xl border border-dashed border-border bg-background/70 px-4 py-6 text-sm text-muted-foreground">
            Enter at least 2 characters to search by use case, stack, or capability.
          </div>
        )}

        {error && deferredQuery.length >= 2 && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            Search request failed. The UI will work again once the API is reachable.
          </div>
        )}

        {isFetching && deferredQuery.length >= 2 && (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-xl border border-border bg-background/60 p-4"
              >
                <div className="mb-2 h-4 w-32 rounded bg-muted" />
                <div className="mb-3 h-3 w-full rounded bg-muted" />
                <div className="mb-2 h-3 w-5/6 rounded bg-muted" />
                <div className="h-3 w-2/3 rounded bg-muted" />
              </div>
            ))}
          </div>
        )}

        {!isFetching &&
          data &&
          deferredQuery.length >= 2 &&
          data.results.length === 0 && (
            <div className="rounded-xl border border-dashed border-border bg-background/70 px-4 py-6 text-sm text-muted-foreground">
              No repositories matched this intent strongly enough. Try a broader
              phrase, lower the star floor, or clear the language filter.
            </div>
          )}

        {!isFetching && data && data.results.length > 0 && (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {data.results.map((result) => {
              const color = CATEGORY_COLORS[result.repo.category] ?? "#6b7280";

              return (
                <button
                  key={result.repo.repo_id}
                  onClick={() => onSelectRepo(result.repo.repo_full_name)}
                  className="group rounded-xl border border-border bg-background/70 p-4 text-left transition-colors hover:border-cyan-400/40 hover:bg-background"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                          style={{ backgroundColor: color }}
                        >
                          {result.repo.category}
                        </span>
                        <span className="text-[11px] text-muted-foreground">
                          score {result.score.toFixed(2)}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="truncate text-sm font-semibold">
                          {result.repo.repo_full_name}
                        </span>
                        <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
                      </div>
                      {result.repo.description && (
                        <p className="mt-1 text-sm text-muted-foreground">
                          {truncate(result.repo.description, 120)}
                        </p>
                      )}
                    </div>

                    <a
                      href={result.repo.html_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(event) => event.stopPropagation()}
                      className="shrink-0 rounded-lg border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
                    >
                      open
                    </a>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {result.matched_terms.slice(0, 5).map((term) => (
                      <span
                        key={term}
                        className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[11px] text-cyan-200"
                      >
                        {term}
                      </span>
                    ))}
                    {result.repo.primary_language && (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                        {result.repo.primary_language}
                      </span>
                    )}
                  </div>

                  <div className="mt-3 space-y-1.5">
                    {result.why_matched.map((reason) => (
                      <div
                        key={reason}
                        className="flex items-start gap-2 text-xs text-muted-foreground"
                      >
                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
                    <div className="flex items-center gap-1 text-amber-300">
                      <Star className="h-3.5 w-3.5" />
                      {formatNumber(result.repo.stargazers_count)}
                    </div>
                    <div className="flex items-center gap-1 text-emerald-300">
                      <TrendingUp className="h-3.5 w-3.5" />
                      +{formatNumber(result.star_count_in_window)} in {days}d
                    </div>
                    <div className="text-muted-foreground">
                      lexical {result.lexical_score.toFixed(2)}
                      {result.semantic_score !== null && (
                        <span className="ml-2">
                          semantic {result.semantic_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
