"use client";

import { TrendingUp, ExternalLink } from "lucide-react";

import { useTrending } from "@/hooks/useDashboard";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
  onSelectRepo: (name: string) => void;
  limit?: number;
  title?: string;
  subtitle?: string;
}

export function TrendingRepos({
  days,
  onSelectRepo,
  limit = 10,
  title = "Weekly Star Growth",
  subtitle = "Repos gaining the most stars since Monday 00:00 GMT+7",
}: Props) {
  const { data, isLoading } = useTrending(days, limit);
  const maxStars = Math.max(...(data ?? []).map((d) => d.star_count_in_window), 1);

  return (
    <div className="card-glow flex flex-col overflow-hidden rounded-[28px] border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <TrendingUp className="h-4 w-4 text-emerald-400" />
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <span className="ml-auto text-xs text-muted-foreground">top {limit}</span>
      </div>

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
          : (data ?? []).slice(0, limit).map((item) => {
              const pct = Math.round((item.star_count_in_window / maxStars) * 100);
              const color =
                CATEGORY_COLORS[item.repo.category] ?? "#6b7280";

              return (
                <button
                  key={item.repo.repo_id}
                  onClick={() => onSelectRepo(item.repo.repo_full_name)}
                  className="w-full border-b border-border/60 px-4 py-3.5 text-left transition-colors hover:bg-muted/40"
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex min-w-0 items-center gap-1.5">
                        <span className="w-5 shrink-0 text-center text-xs font-bold text-muted-foreground">
                          {item.growth_rank}
                        </span>
                        <span className="truncate text-sm font-medium">
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
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                        {item.repo.primary_language && <span>{item.repo.primary_language}</span>}
                        <span
                          className="rounded-full px-2 py-0.5 font-medium text-white"
                          style={{ backgroundColor: color }}
                        >
                          {item.repo.category}
                        </span>
                      </div>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-emerald-500">
                      +{formatNumber(item.star_count_in_window)}
                    </span>
                  </div>

                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>

                  <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
                    <span>
                      Total stars {formatNumber(item.repo.stargazers_count)}
                    </span>
                    <span>
                      Forks {formatNumber(item.repo.forks_count)}
                    </span>
                  </div>
                </button>
              );
            })}
      </div>
    </div>
  );
}
