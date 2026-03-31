"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Flame,
  Layers3,
  Radar,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { useAIMarketBrief } from "@/hooks/useAIMarketBrief";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber, relativeTime, truncate } from "@/lib/utils";

interface Props {
  days: number;
  onSelectRepo: (name: string) => void;
}

export function AIMarketBriefCard({ days, onSelectRepo }: Props) {
  const [isEnabled, setIsEnabled] = useState(false);
  const { data, isLoading, isFetching, error, refetch } = useAIMarketBrief(days, isEnabled);

  useEffect(() => {
    setIsEnabled(false);
  }, [days]);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-rose-500/10 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-amber-300" />
          <h2 className="text-sm font-semibold">AI Market Brief</h2>
        </div>
        <span className="text-xs text-muted-foreground">window: {days}d</span>
      </div>

      <div className="p-4 sm:p-5">
        {!isEnabled ? (
          <div className="rounded-xl border border-dashed border-border bg-background/70 px-4 py-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-sm font-medium">AI generation is on-demand</div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Generate the brief only when needed to avoid loading the language model on
                  every dashboard visit.
                </p>
              </div>
              <button
                onClick={() => setIsEnabled(true)}
                className="rounded-xl border border-amber-400/40 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-200 transition-colors hover:bg-amber-500/15"
              >
                Generate market brief
              </button>
            </div>
          </div>
        ) : isLoading || (isFetching && !data) ? (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
            <div className="space-y-3 animate-pulse">
              <div className="h-5 w-3/5 rounded bg-muted" />
              <div className="h-4 w-full rounded bg-muted" />
              <div className="h-4 w-5/6 rounded bg-muted" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="h-28 rounded-xl bg-muted" />
                <div className="h-28 rounded-xl bg-muted" />
              </div>
            </div>
            <div className="space-y-3 animate-pulse">
              <div className="h-24 rounded-xl bg-muted" />
              <div className="h-24 rounded-xl bg-muted" />
              <div className="h-24 rounded-xl bg-muted" />
            </div>
          </div>
        ) : error || !data ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-200">
            <div>Market brief is temporarily unavailable. Core dashboard analytics remain usable.</div>
            <button
              onClick={() => void refetch()}
              className="mt-3 rounded-lg border border-red-400/40 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-red-500/10"
            >
              Retry brief generation
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                  {data.retrieval_mode === "model" ? "model brief" : "template brief"}
                </span>
                <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-200">
                  {data.breakout_repos.length} breakout repos
                </span>
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                  generated {relativeTime(data.generated_at)}
                </span>
              </div>

              <div>
                <h3 className="text-lg font-semibold">{data.headline}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{data.summary}</p>
              </div>

              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {data.breakout_repos.map((item) => (
                  <button
                    key={item.repo.repo_id}
                    onClick={() => onSelectRepo(item.repo.repo_full_name)}
                    className="group rounded-xl border border-border bg-background/60 p-4 text-left transition-colors hover:border-amber-400/40 hover:bg-background"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                            style={{
                              backgroundColor: CATEGORY_COLORS[item.repo.category] ?? "#6b7280",
                            }}
                          >
                            {item.repo.category}
                          </span>
                          <span className="text-[11px] text-muted-foreground">
                            momentum {item.momentum_score.toFixed(3)}
                          </span>
                        </div>
                        <div className="mt-2 text-sm font-semibold">{item.repo.repo_full_name}</div>
                        {item.repo.description && (
                          <p className="mt-1 text-sm text-muted-foreground">
                            {truncate(item.repo.description, 110)}
                          </p>
                        )}
                      </div>
                      <TrendingUp className="h-4 w-4 shrink-0 text-amber-300 transition-transform group-hover:-translate-y-0.5" />
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded-lg border border-border bg-background/80 p-2">
                        <div className="text-muted-foreground">Stars</div>
                        <div className="mt-1 font-semibold text-amber-300">
                          +{formatNumber(item.star_count_in_window)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-background/80 p-2">
                        <div className="text-muted-foreground">Events</div>
                        <div className="mt-1 font-semibold">
                          {formatNumber(item.total_events_in_window)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-background/80 p-2">
                        <div className="text-muted-foreground">Actors</div>
                        <div className="mt-1 font-semibold text-cyan-300">
                          {formatNumber(item.unique_actors_in_window)}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              <div className="rounded-xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Flame className="h-4 w-4 text-amber-300" />
                  Key Takeaways
                </div>
                <div className="space-y-2">
                  {data.key_takeaways.map((item) => (
                    <div key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-amber-300" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Layers3 className="h-4 w-4 text-orange-300" />
                  Category Movers
                </div>
                <div className="space-y-3">
                  {data.category_movers.map((item) => (
                    <div key={item.category} className="rounded-lg border border-border bg-background/80 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium">{item.category}</span>
                        <span className="text-xs text-muted-foreground">
                          {(item.share_of_window_stars * 100).toFixed(0)}% of surfaced stars
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div>leader: {item.leader_repo_name}</div>
                        <div>active repos: {formatNumber(item.active_repo_count)}</div>
                        <div>stars: +{formatNumber(item.total_stars_in_window)}</div>
                        <div>events: {formatNumber(item.total_events_in_window)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Radar className="h-4 w-4 text-rose-300" />
                  Topic Shifts
                </div>
                <div className="flex flex-wrap gap-2">
                  {data.topic_shifts.map((item) => (
                    <div
                      key={item.topic}
                      className="rounded-full border border-border bg-background/80 px-3 py-1.5 text-xs"
                    >
                      <span className="font-medium text-foreground">{item.topic}</span>
                      <span className="ml-2 text-muted-foreground">
                        +{formatNumber(item.star_count_in_window)} / {formatNumber(item.repo_count)} repos
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <AlertTriangle className="h-4 w-4 text-amber-300" />
                  Watchouts
                </div>
                <div className="space-y-2">
                  {data.watchouts.map((item) => (
                    <div key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-amber-300" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
