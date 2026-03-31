"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeftRight,
  GitCompareArrows,
  GitFork,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";

import { useAIRepoCompare } from "@/hooks/useAIRepoCompare";
import { useTrending } from "@/hooks/useDashboard";
import { CATEGORY_COLORS } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

interface Props {
  baseRepoName: string | null;
  days: number;
}

const REPO_PATTERN = /^[^/]+\/[^/]+$/;

function EmptyState() {
  return (
    <div className="flex h-full min-h-[260px] items-center justify-center text-muted-foreground">
      <div className="max-w-md text-center">
        <GitCompareArrows className="mx-auto mb-3 h-10 w-10 text-sky-400/60" />
        <p className="text-sm font-medium text-foreground">AI Repo Compare</p>
        <p className="mt-2 text-sm">
          Select a repository first, then compare it against another repo to expose
          tradeoffs, momentum, and ecosystem depth.
        </p>
      </div>
    </div>
  );
}

export function AIRepoCompareCard({ baseRepoName, days }: Props) {
  const [draftRepo, setDraftRepo] = useState("");
  const [activeCompareRepo, setActiveCompareRepo] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const { data: trendingData } = useTrending(days);
  const { data, isLoading, error } = useAIRepoCompare(
    baseRepoName,
    activeCompareRepo,
    days,
  );

  useEffect(() => {
    setDraftRepo("");
    setActiveCompareRepo(null);
    setValidationError(null);
  }, [baseRepoName, days]);

  function submitCompareTarget(repoName: string) {
    const normalized = repoName.trim();
    if (!REPO_PATTERN.test(normalized)) {
      setValidationError("Use owner/repo format for the comparison repo.");
      return;
    }
    if (normalized === baseRepoName) {
      setValidationError("Choose a different repository for comparison.");
      return;
    }
    setValidationError(null);
    setDraftRepo(normalized);
    setActiveCompareRepo(normalized);
  }

  const quickPicks = (trendingData ?? [])
    .map((item) => item.repo.repo_full_name)
    .filter((repoName) => repoName !== baseRepoName)
    .slice(0, 5);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-indigo-500/10 via-sky-500/10 to-cyan-500/10 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="h-4 w-4 text-sky-300" />
          <h2 className="text-sm font-semibold">
            {baseRepoName ? (
              <>
                AI Repo Compare <span className="text-primary">from {baseRepoName}</span>
              </>
            ) : (
              "AI Repo Compare"
            )}
          </h2>
        </div>
        {baseRepoName && (
          <span className="text-xs text-muted-foreground">window: {days}d</span>
        )}
      </div>

      <div className="p-4 sm:p-5">
        {!baseRepoName ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row">
              <input
                value={draftRepo}
                onChange={(event) => setDraftRepo(event.target.value)}
                placeholder="Compare against owner/repo"
                className="flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground"
              />
              <button
                onClick={() => submitCompareTarget(draftRepo)}
                className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Compare
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">Quick picks:</span>
              {quickPicks.length > 0 ? (
                quickPicks.map((repoName) => (
                  <button
                    key={repoName}
                    onClick={() => submitCompareTarget(repoName)}
                    className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-sky-400/50 hover:text-foreground"
                  >
                    {repoName}
                  </button>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">
                  trending suggestions will appear here
                </span>
              )}
            </div>

            {validationError && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                {validationError}
              </div>
            )}

            {!activeCompareRepo && !validationError && (
              <div className="rounded-xl border border-dashed border-border bg-background/60 px-4 py-5 text-sm text-muted-foreground">
                Compare the selected repo against another candidate to highlight
                momentum, audience breadth, and ecosystem maturity.
              </div>
            )}

            {activeCompareRepo && isLoading && (
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
                <div className="space-y-3 animate-pulse">
                  <div className="h-5 w-3/5 rounded bg-muted" />
                  <div className="h-4 w-full rounded bg-muted" />
                  <div className="h-4 w-5/6 rounded bg-muted" />
                  <div className="h-28 rounded-xl bg-muted" />
                </div>
                <div className="space-y-3 animate-pulse">
                  <div className="h-24 rounded-xl bg-muted" />
                  <div className="h-24 rounded-xl bg-muted" />
                </div>
              </div>
            )}

            {activeCompareRepo && error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                Repo comparison is temporarily unavailable.
              </div>
            )}

            {data && (
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                      {data.retrieval_mode === "model" ? "model compare" : "template compare"}
                    </span>
                    <span className="rounded-full bg-sky-500/10 px-2.5 py-1 text-[11px] text-sky-200">
                      winner: {data.overall_winner}
                    </span>
                    <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                      {data.base_repo.repo_full_name} vs {data.compare_repo.repo_full_name}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold">{data.headline}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{data.summary}</p>
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-border bg-background/60 p-4">
                      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                        <Sparkles className="h-4 w-4 text-sky-300" />
                        Choose {data.base_repo.repo_name}
                      </div>
                      <div className="space-y-2">
                        {data.when_to_choose_base.map((item) => (
                          <div key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-sky-300" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-xl border border-border bg-background/60 p-4">
                      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                        <Sparkles className="h-4 w-4 text-emerald-300" />
                        Choose {data.compare_repo.repo_name}
                      </div>
                      <div className="space-y-2">
                        {data.when_to_choose_compare.map((item) => (
                          <div key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-emerald-300" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border bg-background/60 p-4">
                    <div className="mb-3 text-sm font-medium">Key Differences</div>
                    <div className="space-y-2">
                      {data.key_differences.map((difference) => (
                        <div key={difference} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-300" />
                          <span>{difference}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  {data.metric_snapshot.map((metric) => {
                    const winnerColor =
                      metric.winner === "base"
                        ? CATEGORY_COLORS[data.base_repo.category] ?? "#38bdf8"
                        : metric.winner === "compare"
                          ? CATEGORY_COLORS[data.compare_repo.category] ?? "#10b981"
                          : "#6b7280";
                    const Icon =
                      metric.key === "actors"
                        ? Users
                        : metric.key === "forks"
                          ? GitFork
                          : TrendingUp;

                    return (
                      <div
                        key={metric.key}
                        className="rounded-xl border border-border bg-background/60 p-4"
                      >
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2 text-sm font-medium">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                            {metric.label}
                          </div>
                          <span
                            className="rounded-full px-2 py-0.5 text-[11px] font-medium text-white"
                            style={{ backgroundColor: winnerColor }}
                          >
                            {metric.winner}
                          </span>
                        </div>

                        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-sm">
                          <div className="min-w-0">
                            <div className="truncate text-[11px] text-muted-foreground">
                              {data.base_repo.repo_name}
                            </div>
                            <div className="text-base font-semibold">
                              {formatNumber(metric.base_value)}
                            </div>
                          </div>
                          <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
                          <div className="min-w-0 text-right">
                            <div className="truncate text-[11px] text-muted-foreground">
                              {data.compare_repo.repo_name}
                            </div>
                            <div className="text-base font-semibold">
                              {formatNumber(metric.compare_value)}
                            </div>
                          </div>
                        </div>

                        <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn("h-full")}
                            style={{
                              width: `${Math.max(
                                10,
                                metric.base_value + metric.compare_value === 0
                                  ? 50
                                  : (metric.base_value / (metric.base_value + metric.compare_value)) * 100,
                              )}%`,
                              backgroundColor:
                                CATEGORY_COLORS[data.base_repo.category] ?? "#38bdf8",
                            }}
                          />
                          <div
                            className={cn("h-full")}
                            style={{
                              width: `${Math.max(
                                10,
                                metric.base_value + metric.compare_value === 0
                                  ? 50
                                  : (metric.compare_value / (metric.base_value + metric.compare_value)) * 100,
                              )}%`,
                              backgroundColor:
                                CATEGORY_COLORS[data.compare_repo.category] ?? "#10b981",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
