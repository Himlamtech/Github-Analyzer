"use client";

import type { ReactNode } from "react";
import { ArrowUpRight, Flame, Rocket, Users } from "lucide-react";

import { useShockMovers } from "@/hooks/useDashboard";
import { CATEGORY_COLORS } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
  onSelectRepo: (name: string) => void;
}

export function WeekInReview({ days, onSelectRepo }: Props) {
  const { data, isLoading, error } = useShockMovers(days);
  const topAbsolute = data?.absolute_movers[0];
  const topPercentage = data?.percentage_movers[0];

  return (
    <section className="card-glow overflow-hidden rounded-[28px] border border-border bg-card">
      <div className="border-b border-border bg-gradient-to-r from-slate-950 via-sky-950 to-cyan-950 px-4 py-5 text-white sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Flame className="h-4 w-4 text-cyan-300" />
              This Week Changed
            </div>
            <p className="max-w-3xl text-sm text-sky-100/76">
              Lead with delta, not inventory. This band compresses the strongest absolute
              and percentage movers into one editorial snapshot.
            </p>
          </div>
          <div className="text-xs text-sky-100/68">window: last {days}d</div>
        </div>

        {!isLoading && !error && data && (
          <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_220px]">
            <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur-sm">
              <div className="text-[11px] uppercase tracking-[0.18em] text-cyan-200">
                Biggest Absolute Mover
              </div>
              <div className="mt-2 text-lg font-semibold text-white">
                {topAbsolute?.repo.repo_full_name ?? "No standout repo yet"}
              </div>
              <p className="mt-1 text-sm text-sky-100/74">
                {topAbsolute
                  ? `+${formatNumber(topAbsolute.star_count_in_window)} stars from ${formatNumber(
                      topAbsolute.unique_actors_in_window,
                    )} active actors.`
                  : "No repo crossed the current breakout threshold in this window."}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur-sm">
              <div className="text-[11px] uppercase tracking-[0.18em] text-emerald-200">
                Sharpest Percentage Gainer
              </div>
              <div className="mt-2 text-lg font-semibold text-white">
                {topPercentage?.repo.repo_full_name ?? "No breakout gainer yet"}
              </div>
              <p className="mt-1 text-sm text-sky-100/74">
                {topPercentage
                  ? `+${topPercentage.weekly_percent_gain.toFixed(1)}% versus its baseline, with ${formatNumber(
                      topPercentage.star_count_in_window,
                    )} stars in the current window.`
                  : "No repo met the current baseline guardrail for percentage growth."}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur-sm">
              <div className="text-[11px] uppercase tracking-[0.18em] text-sky-200">
                Reading lens
              </div>
              <p className="mt-2 text-sm leading-6 text-sky-100/74">
                Absolute growth captures raw demand. Percentage growth catches new
                breakouts before they look large on market cap alone.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 p-4 sm:p-5 xl:grid-cols-2">
        <MoverColumn
          title="Most Stars Added"
          icon={<Rocket className="h-4 w-4 text-blue-500" />}
          movers={data?.absolute_movers ?? []}
          isLoading={isLoading}
          onSelectRepo={onSelectRepo}
        />
        <MoverColumn
          title="Highest % Growth"
          icon={<Users className="h-4 w-4 text-cyan-500" />}
          movers={data?.percentage_movers ?? []}
          isLoading={isLoading}
          onSelectRepo={onSelectRepo}
        />
      </div>
    </section>
  );
}

function MoverColumn({
  title,
  icon,
  movers,
  isLoading,
  onSelectRepo,
}: {
  title: string;
  icon: ReactNode;
  movers: {
    repo: { repo_full_name: string; category: string; html_url: string };
    star_count_in_window: number;
    previous_star_count_in_window: number;
    unique_actors_in_window: number;
    weekly_percent_gain: number;
    rank: number;
  }[];
  isLoading: boolean;
  onSelectRepo: (name: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-border bg-background/60">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        {icon}
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="divide-y divide-border/60">
        {isLoading &&
          Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="animate-pulse px-4 py-3">
              <div className="mb-2 h-4 w-40 rounded bg-muted" />
              <div className="h-3 w-full rounded bg-muted" />
            </div>
          ))}

        {!isLoading &&
          movers.map((mover) => (
            <button
              key={`${title}-${mover.repo.repo_full_name}`}
              onClick={() => onSelectRepo(mover.repo.repo_full_name)}
              className="w-full px-4 py-3 text-left transition-colors hover:bg-muted/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-muted-foreground">
                      {mover.rank}
                    </span>
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white"
                      style={{
                        backgroundColor:
                          CATEGORY_COLORS[mover.repo.category] ?? "#6b7280",
                      }}
                    >
                      {mover.repo.category}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="truncate text-sm font-semibold">
                      {mover.repo.repo_full_name}
                    </span>
                    <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>+{formatNumber(mover.star_count_in_window)} stars</span>
                    <span>{formatNumber(mover.unique_actors_in_window)} actors</span>
                    <span>{mover.weekly_percent_gain.toFixed(1)}% gain</span>
                  </div>
                </div>
                <a
                  href={mover.repo.html_url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(event) => event.stopPropagation()}
                  className="shrink-0 text-xs text-muted-foreground hover:text-foreground"
                >
                  open
                </a>
              </div>

              <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(mover.weekly_percent_gain, 100)}%`,
                    backgroundColor: CATEGORY_COLORS[mover.repo.category] ?? "#6b7280",
                  }}
                />
              </div>

              <div className="mt-2 text-xs text-muted-foreground">
                Previous window: +{formatNumber(mover.previous_star_count_in_window)} stars
              </div>
            </button>
          ))}

        {!isLoading && movers.length === 0 && (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            No movers crossed the current threshold in this window.
          </div>
        )}
      </div>
    </div>
  );
}
