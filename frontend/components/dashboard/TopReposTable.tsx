"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { ExternalLink, GitFork, Sparkles, Star, TrendingUp } from "lucide-react";

import { useTopRepos } from "@/hooks/useDashboard";
import { CATEGORY_COLORS, type Category } from "@/lib/types";
import { formatNumber, truncate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  category: Category;
  days: number;
  selectedRepo: string | null;
  onSelectRepo: (name: string) => void;
}

function SkeletonRow() {
  return (
    <div className="animate-pulse rounded-2xl border border-border/70 bg-background/50 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-9 w-9 rounded-full bg-muted" />
        <div className="flex-1">
          <div className="mb-2 h-4 w-40 rounded bg-muted" />
          <div className="h-3 w-56 rounded bg-muted" />
        </div>
      </div>
      <div className="mb-3 h-2 w-full rounded-full bg-muted" />
      <div className="flex gap-3">
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-3 w-16 rounded bg-muted" />
      </div>
    </div>
  );
}

export function TopReposTable({ category, days, selectedRepo, onSelectRepo }: Props) {
  const { data, isLoading } = useTopRepos(category, days);
  const repos = (data ?? []).slice(0, 20);
  const maxStars = Math.max(...repos.map((item) => item.repo.stargazers_count), 1);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border bg-gradient-to-r from-sky-500/10 via-blue-500/10 to-cyan-400/10 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="h-4 w-4 text-blue-400" />
              Top 20 Repositories
            </div>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Rank by total stars, but keep weekly momentum visible so market leaders do
              not hide newer breakouts.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full border border-border bg-background/80 px-3 py-1">
              window: last {days}d
            </span>
            <span className="rounded-full border border-border bg-background/80 px-3 py-1">
              showing {repos.length}
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-3 p-4 sm:p-5">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
          : repos.map((item, idx) => {
              const repo = item.repo;
              const color = CATEGORY_COLORS[repo.category] ?? "#6b7280";
              const isSelected = selectedRepo === repo.repo_full_name;
              const width = Math.max(
                10,
                Math.round((repo.stargazers_count / maxStars) * 100),
              );

              return (
                <button
                  key={repo.repo_id}
                  onClick={() => onSelectRepo(repo.repo_full_name)}
                  className={cn(
                    "group relative overflow-hidden rounded-2xl border p-4 text-left transition-all",
                    isSelected
                      ? "border-blue-400/60 bg-blue-500/10 shadow-[0_14px_40px_-26px_rgba(59,130,246,0.45)]"
                      : "border-border bg-background/60 hover:border-blue-400/35 hover:bg-background",
                  )}
                >
                  <div
                    className="pointer-events-none absolute inset-y-0 left-0 rounded-r-full opacity-20 transition-all"
                    style={{
                      width: `${width}%`,
                      background: `linear-gradient(90deg, ${color}, transparent)`,
                    }}
                  />

                  <div className="relative flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-background/90 text-sm font-bold text-muted-foreground">
                          {idx + 1}
                        </div>
                        <Image
                          src={repo.owner_avatar_url || "https://avatars.githubusercontent.com/u/0"}
                          alt={repo.owner_login}
                          width={36}
                          height={36}
                          className="shrink-0 rounded-full"
                          unoptimized
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                              style={{ backgroundColor: color }}
                            >
                              {repo.category}
                            </span>
                            {repo.primary_language && (
                              <span className="rounded-full border border-border bg-background/90 px-2 py-0.5 text-[10px] text-muted-foreground">
                                {repo.primary_language}
                              </span>
                            )}
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <a
                              href={repo.html_url}
                              target="_blank"
                              rel="noreferrer"
                              className="truncate text-sm font-semibold hover:text-primary"
                              onClick={(event) => event.stopPropagation()}
                            >
                              {repo.repo_full_name}
                            </a>
                            <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
                          </div>
                          {repo.description && (
                            <p className="mt-1 text-sm text-muted-foreground">
                              {truncate(repo.description, 110)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="relative grid shrink-0 grid-cols-3 gap-3 xl:min-w-[340px]">
                      <MetricChip
                        icon={<Star className="h-3.5 w-3.5 text-amber-300" />}
                        label="Stars"
                        value={formatNumber(repo.stargazers_count)}
                      />
                      <MetricChip
                        icon={<TrendingUp className="h-3.5 w-3.5 text-emerald-300" />}
                        label={`${days}d raise`}
                        value={`+${formatNumber(item.star_count_in_window)}`}
                        emphasize
                      />
                      <MetricChip
                        icon={<GitFork className="h-3.5 w-3.5 text-sky-300" />}
                        label="Forks"
                        value={formatNumber(repo.forks_count)}
                      />
                    </div>
                  </div>
                </button>
              );
            })}

        {!isLoading && repos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-background/60 px-4 py-8 text-sm text-muted-foreground">
            No repositories matched the current category and time window.
          </div>
        )}
      </div>
    </section>
  );
}

function MetricChip({
  icon,
  label,
  value,
  emphasize = false,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-3 py-2",
        emphasize
          ? "border-emerald-400/25 bg-emerald-500/10"
          : "border-border bg-background/80",
      )}
    >
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  );
}
