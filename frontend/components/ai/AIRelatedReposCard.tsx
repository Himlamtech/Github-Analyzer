"use client";

import { ArrowUpRight, Network, Orbit, Sparkles, Star, TrendingUp } from "lucide-react";

import { useAIRelatedRepos } from "@/hooks/useAIRelatedRepos";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber, truncate } from "@/lib/utils";

interface Props {
  repoName: string | null;
  days: number;
  onSelectRepo: (name: string) => void;
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-[240px] items-center justify-center text-muted-foreground">
      <div className="max-w-md text-center">
        <Network className="mx-auto mb-3 h-10 w-10 text-indigo-400/60" />
        <p className="text-sm font-medium text-foreground">Ecosystem Neighbors</p>
        <p className="mt-2 text-sm">
          Select a repository to surface nearby projects in the same ecosystem and
          momentum band.
        </p>
      </div>
    </div>
  );
}

export function AIRelatedReposCard({ repoName, days, onSelectRepo }: Props) {
  const { data, isLoading, error } = useAIRelatedRepos(repoName, days, 6);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-violet-500/10 via-indigo-500/10 to-sky-500/10 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <Orbit className="h-4 w-4 text-indigo-300" />
          <h2 className="text-sm font-semibold">
            {repoName ? (
              <>
                Ecosystem Neighbors <span className="text-primary">for {repoName}</span>
              </>
            ) : (
              "Ecosystem Neighbors"
            )}
          </h2>
        </div>
        {repoName && (
          <span className="text-xs text-muted-foreground">window: {days}d</span>
        )}
      </div>

      <div className="p-4 sm:p-5">
        {!repoName ? (
          <EmptyState />
        ) : isLoading ? (
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-xl border border-border bg-background/60 p-4"
              >
                <div className="mb-2 h-4 w-32 rounded bg-muted" />
                <div className="mb-3 h-3 w-full rounded bg-muted" />
                <div className="h-16 rounded-xl bg-muted" />
              </div>
            ))}
          </div>
        ) : error || !data ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            Related repository recommendations are temporarily unavailable.
          </div>
        ) : data.results.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-background/60 px-4 py-5 text-sm text-muted-foreground">
            No close neighbors found for this repository in the current window.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-indigo-300" />
              {data.returned_results} neighbors from {data.total_candidates} candidates
            </div>

            <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              {data.results.map((result) => {
                const color = CATEGORY_COLORS[result.repo.category] ?? "#6b7280";

                return (
                  <button
                    key={result.repo.repo_id}
                    onClick={() => onSelectRepo(result.repo.repo_full_name)}
                    className="group rounded-xl border border-border bg-background/70 p-4 text-left transition-colors hover:border-indigo-400/40 hover:bg-background"
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
                            similarity {result.similarity_score.toFixed(2)}
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
                            {truncate(result.repo.description, 110)}
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
                      {result.shared_topics.slice(0, 4).map((topic) => (
                        <span
                          key={topic}
                          className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[11px] text-indigo-200"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>

                    <div className="mt-3 space-y-1.5">
                      {result.why_related.map((reason) => (
                        <div
                          key={reason}
                          className="flex items-start gap-2 text-xs text-muted-foreground"
                        >
                          <span className="mt-1 h-1.5 w-1.5 rounded-full bg-indigo-300" />
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
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
