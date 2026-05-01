"use client";

import { AlertTriangle, BrainCircuit, Flame, GitBranch, Sparkles } from "lucide-react";

import { useAIRepoBrief } from "@/hooks/useAIRepoBrief";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/utils";

interface Props {
  repoName: string | null;
  days: number;
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-[280px] items-center justify-center text-muted-foreground">
      <div className="max-w-md text-center">
        <BrainCircuit className="mx-auto mb-3 h-10 w-10 text-cyan-400/60" />
        <p className="text-sm font-medium text-foreground">AI Repo Brief</p>
        <p className="mt-2 text-sm">
          Select a repository from the dashboard or AI search to generate a grounded brief
          explaining why it matters now.
        </p>
      </div>
    </div>
  );
}

export function AIRepoBriefCard({ repoName, days }: Props) {
  const { data, isLoading, error } = useAIRepoBrief(repoName, days);

  return (
    <section className="card-glow overflow-hidden rounded-[28px] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-emerald-500/10 via-cyan-500/10 to-sky-500/10 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-400" />
          <h2 className="text-sm font-semibold">
            {repoName ? (
              <>
                AI Repo Brief <span className="text-primary">for {repoName}</span>
              </>
            ) : (
              "AI Repo Brief"
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
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
            <div className="space-y-3 animate-pulse">
              <div className="h-5 w-3/5 rounded bg-muted" />
              <div className="h-4 w-full rounded bg-muted" />
              <div className="h-4 w-5/6 rounded bg-muted" />
              <div className="h-20 rounded-xl bg-muted" />
            </div>
            <div className="space-y-3 animate-pulse">
              <div className="h-24 rounded-xl bg-muted" />
              <div className="h-24 rounded-xl bg-muted" />
            </div>
          </div>
        ) : error || !data ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            Repo brief is temporarily unavailable. The charts remain usable while the AI
            layer recovers.
          </div>
        ) : (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
              <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-white"
                  style={{
                    backgroundColor: CATEGORY_COLORS[data.repo.category] ?? "#6b7280",
                  }}
                >
                  {data.repo.category}
                </span>
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                  {data.retrieval_mode === "model" ? "model brief" : "template brief"}
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-200">
                  {data.trend_verdict}
                </span>
                {data.latest_event_at && (
                  <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                    latest event {relativeTime(data.latest_event_at)}
                  </span>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold">{data.headline}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{data.summary}</p>
              </div>

              <div className="rounded-2xl border border-border bg-background/60 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Flame className="h-4 w-4 text-amber-300" />
                  Why Trending
                </div>
                <p className="text-sm leading-6 text-muted-foreground">{data.why_trending}</p>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-border bg-background/60 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Stars In Window
                  </div>
                  <div className="mt-1 text-xl font-semibold text-amber-300">
                    +{formatNumber(data.star_count_in_window)}
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Total Events
                  </div>
                  <div className="mt-1 text-xl font-semibold">
                    {formatNumber(data.total_events_in_window)}
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    Unique Actors
                  </div>
                  <div className="mt-1 text-xl font-semibold text-cyan-300">
                    {formatNumber(data.unique_actors_in_window)}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <GitBranch className="h-4 w-4 text-cyan-300" />
                  Key Signals
                </div>
                <div className="space-y-2">
                  {data.key_signals.map((signal) => (
                    <div key={signal} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-cyan-300" />
                      <span>{signal}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <AlertTriangle className="h-4 w-4 text-amber-300" />
                  Watchouts
                </div>
                <div className="space-y-2">
                  {data.watchouts.map((watchout) => (
                    <div key={watchout} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-amber-300" />
                      <span>{watchout}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-background/60 p-4">
                <div className="mb-3 text-sm font-medium">Activity Breakdown</div>
                <div className="space-y-2">
                  {data.activity_breakdown.length > 0 ? (
                    data.activity_breakdown.map((item) => (
                      <div key={item.event_type} className="flex items-center justify-between gap-3 text-sm">
                        <span className="text-muted-foreground">{item.event_type}</span>
                        <span className="font-mono text-xs">{formatNumber(item.event_count)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted-foreground">No recent event breakdown available.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
