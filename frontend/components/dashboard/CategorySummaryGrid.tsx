"use client";

import { ExternalLink, Layers3, Star } from "lucide-react";

import { useCategorySummary } from "@/hooks/useDashboard";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/lib/types";
import { formatNumber, formatDelta } from "@/lib/utils";

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-border bg-background/60 p-4">
      <div className="mb-3 h-4 w-24 rounded bg-muted" />
      <div className="mb-2 h-8 w-24 rounded bg-muted" />
      <div className="h-3 w-32 rounded bg-muted" />
    </div>
  );
}

export function CategorySummaryGrid() {
  const { data, isLoading } = useCategorySummary();
  const categories = [...(data ?? [])].sort((left, right) => {
    return right.total_stars - left.total_stars;
  });
  const leader = categories[0];
  const maxStars = Math.max(...categories.map((item) => item.total_stars), 1);

  if (isLoading) {
    return (
      <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <div className="h-4 w-28 rounded bg-muted" />
        </div>
        <div className="grid gap-4 p-4 lg:grid-cols-[1.1fr_1.4fr]">
          <SkeletonCard />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border bg-gradient-to-r from-violet-500/10 via-fuchsia-500/10 to-orange-500/10 px-4 py-4 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Layers3 className="h-4 w-4 text-violet-300" />
              Top Categories
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Market taxonomy leaders by total stars, with weekly movement kept visible.
            </p>
          </div>
          <div className="rounded-full border border-border bg-background/80 px-3 py-1 text-xs text-muted-foreground">
            {categories.length} tracked
          </div>
        </div>
      </div>

      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[1.1fr_1.4fr]">
        {leader ? (
          <div
            className="rounded-3xl border p-5 text-white shadow-[0_20px_60px_-34px_rgba(76,29,149,0.55)]"
            style={{
              background: `linear-gradient(135deg, ${
                CATEGORY_COLORS[leader.category] ?? "#6b7280"
              }, rgba(15, 23, 42, 0.92))`,
            }}
          >
            <div className="text-xs uppercase tracking-[0.22em] text-white/70">
              Current Leader
            </div>
            <div className="mt-3 text-2xl font-semibold">
              {CATEGORY_LABELS[leader.category] ?? leader.category}
            </div>
            <div className="mt-6 flex items-end gap-2">
              <Star className="mb-1 h-5 w-5 text-amber-300" />
              <span className="text-4xl font-bold tracking-tight">
                {formatNumber(leader.total_stars)}
              </span>
            </div>
            <div className="mt-2 text-sm text-white/80">{leader.repo_count} repos tracked</div>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-white/15 bg-white/10 p-3">
                <div className="text-[11px] uppercase tracking-wide text-white/65">
                  Weekly raise
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {formatDelta(leader.weekly_star_delta)}
                </div>
              </div>
              <div className="rounded-2xl border border-white/15 bg-white/10 p-3">
                <div className="text-[11px] uppercase tracking-wide text-white/65">
                  Lead repo
                </div>
                <div className="mt-1 truncate text-sm font-medium">
                  {leader.top_repo_name || "N/A"}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border bg-background/60 px-4 py-8 text-sm text-muted-foreground">
            No category summary available.
          </div>
        )}

        <div className="space-y-3">
          {categories.map((item, index) => {
            const color = CATEGORY_COLORS[item.category] ?? "#6b7280";
            const label = CATEGORY_LABELS[item.category] ?? item.category;
            const width = Math.max(
              10,
              Math.round((item.total_stars / maxStars) * 100),
            );

            return (
              <div
                key={item.category}
                className="rounded-2xl border border-border bg-background/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="w-5 shrink-0 text-center text-xs font-bold text-muted-foreground">
                        {index + 1}
                      </span>
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="truncate text-sm font-semibold">{label}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>{item.repo_count} repos</span>
                      <span className="text-emerald-400">
                        {formatDelta(item.weekly_star_delta)} / week
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">
                      {formatNumber(item.total_stars)}
                    </div>
                    {item.top_repo_name && (
                      <a
                        href={`https://github.com/${item.top_repo_name}`}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 flex items-center justify-end gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <span className="truncate">
                          {item.top_repo_name.split("/")[1]}
                        </span>
                      </a>
                    )}
                  </div>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${width}%`, backgroundColor: color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
