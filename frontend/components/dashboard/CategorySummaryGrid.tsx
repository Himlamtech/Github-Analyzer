"use client";

import { ExternalLink, Star, TrendingUp } from "lucide-react";

import { useCategorySummary } from "@/hooks/useDashboard";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/lib/types";
import { formatNumber, formatDelta } from "@/lib/utils";
import { cn } from "@/lib/utils";

function SkeletonCard() {
  return (
    <div className="card-glow animate-pulse rounded-xl border border-border bg-card p-4">
      <div className="mb-3 h-4 w-24 rounded bg-muted" />
      <div className="mb-2 h-8 w-20 rounded bg-muted" />
      <div className="h-3 w-32 rounded bg-muted" />
    </div>
  );
}

export function CategorySummaryGrid() {
  const { data, isLoading } = useCategorySummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {(data ?? []).map((item) => {
        const color = CATEGORY_COLORS[item.category] ?? "#6b7280";
        const label = CATEGORY_LABELS[item.category] ?? item.category;

        return (
          <div
            key={item.category}
            className="card-glow rounded-2xl border border-border bg-card p-4 transition-shadow hover:shadow-md"
          >
            <div className="mb-2 flex items-center gap-1.5">
              <div
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs font-medium text-muted-foreground">
                {label}
              </span>
            </div>

            <div className="mb-1 flex items-baseline gap-1">
              <Star className="mt-0.5 h-3.5 w-3.5 text-amber-400" />
              <span className="text-xl font-bold tracking-tight">
                {formatNumber(item.total_stars)}
              </span>
            </div>

            <div className="mb-2 text-xs text-muted-foreground">
              {item.repo_count} repos
            </div>

            <div
              className={cn(
                "flex items-center gap-0.5 text-xs font-medium",
                item.weekly_star_delta > 0 ? "text-emerald-400" : "text-muted-foreground",
              )}
            >
              <TrendingUp className="h-3 w-3" />
              {formatDelta(item.weekly_star_delta)} / week
            </div>

            {item.top_repo_name && (
              <a
                href={`https://github.com/${item.top_repo_name}`}
                target="_blank"
                rel="noreferrer"
                className="mt-2 flex items-center gap-1 truncate text-xs text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-3 w-3 shrink-0" />
                <span className="truncate">{item.top_repo_name.split("/")[1]}</span>
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
