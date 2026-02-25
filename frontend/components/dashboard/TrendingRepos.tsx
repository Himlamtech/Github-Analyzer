"use client";

import { TrendingUp, ExternalLink } from "lucide-react";

import { useTrending } from "@/hooks/useDashboard";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
  onSelectRepo: (name: string) => void;
}

export function TrendingRepos({ days, onSelectRepo }: Props) {
  const { data, isLoading } = useTrending(days);
  const maxStars = Math.max(...(data ?? []).map((d) => d.star_count_in_window), 1);

  return (
    <div className="card-glow flex flex-col overflow-hidden rounded-xl border border-border bg-card">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <TrendingUp className="h-4 w-4 text-emerald-400" />
        <h2 className="text-sm font-semibold">Trending</h2>
        <span className="ml-auto text-xs text-muted-foreground">last {days}d</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading
          ? Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className="animate-pulse border-b border-border/60 px-4 py-3"
              >
                <div className="mb-1.5 h-3.5 w-40 rounded bg-muted" />
                <div className="h-2 w-full rounded-full bg-muted" />
              </div>
            ))
          : (data ?? []).slice(0, 10).map((item) => {
              const pct = Math.round((item.star_count_in_window / maxStars) * 100);
              const color =
                CATEGORY_COLORS[item.repo.category] ?? "#6b7280";

              return (
                <button
                  key={item.repo.repo_id}
                  onClick={() => onSelectRepo(item.repo.repo_full_name)}
                  className="w-full border-b border-border/60 px-4 py-3 text-left transition-colors hover:bg-muted/40"
                >
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="w-5 shrink-0 text-center text-xs font-bold text-muted-foreground">
                        {item.growth_rank}
                      </span>
                      <span className="truncate text-xs font-medium">
                        {item.repo.repo_full_name}
                      </span>
                      <a
                        href={item.repo.html_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="shrink-0"
                      >
                        <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                      </a>
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-emerald-400">
                      +{formatNumber(item.star_count_in_window)}
                    </span>
                  </div>

                  {/* Velocity bar */}
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>

                  {/* Language + category */}
                  <div className="mt-1 flex items-center gap-2">
                    {item.repo.primary_language && (
                      <span className="text-[10px] text-muted-foreground">
                        {item.repo.primary_language}
                      </span>
                    )}
                    <span
                      className="rounded px-1 py-0.5 text-[10px] font-medium text-white"
                      style={{ backgroundColor: color }}
                    >
                      {item.repo.category}
                    </span>
                  </div>
                </button>
              );
            })}
      </div>
    </div>
  );
}
