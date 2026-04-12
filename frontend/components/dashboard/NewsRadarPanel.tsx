"use client";

import { Newspaper, ArrowUpRight } from "lucide-react";

import { useNewsRadar } from "@/hooks/useDashboard";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber, truncate } from "@/lib/utils";

interface Props {
  days: number;
  onSelectRepo: (name: string) => void;
}

export function NewsRadarPanel({ days, onSelectRepo }: Props) {
  const { data, isLoading, error } = useNewsRadar(days);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Newspaper className="h-4 w-4 text-rose-300" />
        <h2 className="text-sm font-semibold">News Radar</h2>
        <span className="ml-auto text-xs text-muted-foreground">external signal</span>
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        {isLoading &&
          Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="animate-pulse rounded-2xl border border-border bg-background/60 p-4"
            >
              <div className="mb-2 h-4 w-40 rounded bg-muted" />
              <div className="mb-3 h-3 w-full rounded bg-muted" />
              <div className="h-3 w-2/3 rounded bg-muted" />
            </div>
          ))}

        {error && (
          <div className="rounded-xl border border-border bg-background/60 px-4 py-6 text-sm text-muted-foreground">
            News radar is unavailable right now. The rest of the dashboard remains usable
            while the external search layer reconnects.
          </div>
        )}

        {!isLoading &&
          !error &&
          (data?.repos ?? []).map((repo) => (
            <div
              key={repo.repo_full_name}
              className="rounded-2xl border border-border bg-background/60 p-4"
            >
              <button
                onClick={() => onSelectRepo(repo.repo_full_name)}
                className="flex w-full items-start justify-between gap-3 text-left"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                      style={{
                        backgroundColor: CATEGORY_COLORS[repo.category] ?? "#6b7280",
                      }}
                    >
                      {repo.category}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      +{formatNumber(repo.star_count_in_window)} stars
                    </span>
                    <span className="text-xs text-rose-200">
                      +{repo.weekly_percent_gain.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-2 text-sm font-semibold">{repo.repo_full_name}</div>
                </div>
                <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>

              <div className="mt-3 space-y-2">
                {repo.headlines.slice(0, 3).map((headline) => (
                  <a
                    key={headline.url}
                    href={headline.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block rounded-xl border border-border/70 bg-card/70 px-3 py-3 transition-colors hover:border-rose-300/40"
                  >
                    <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      {headline.source}
                    </div>
                    <div className="mt-1 text-sm font-medium">{headline.title}</div>
                    {headline.snippet && (
                      <div className="mt-1 text-xs leading-5 text-muted-foreground">
                        {truncate(headline.snippet, 140)}
                      </div>
                    )}
                  </a>
                ))}
                {repo.headlines.length === 0 && (
                  <div className="rounded-xl border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">
                    No strong external headlines found for this repo in the current
                    window.
                  </div>
                )}
              </div>
            </div>
          ))}

        {!isLoading && !error && (data?.repos.length ?? 0) === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-background/60 px-4 py-6 text-sm text-muted-foreground">
            No breakout repositories were strong enough to power the external news radar.
          </div>
        )}
      </div>
    </section>
  );
}
