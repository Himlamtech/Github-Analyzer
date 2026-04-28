"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { BotMessageSquare, LayoutDashboard, Search, TrendingUp } from "lucide-react";

import { CategorySummaryGrid } from "@/components/dashboard/CategorySummaryGrid";
import { WeekInReview } from "@/components/dashboard/WeekInReview";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { useCategorySummary, useTopicRotation } from "@/hooks/useDashboard";
import { formatNumber } from "@/lib/utils";

const QUICK_ACTIONS = [
  {
    href: "/dashboard",
    title: "Open market dashboard",
    description: "Leaderboard, topic rotation, category movement, and ecosystem charts.",
    icon: LayoutDashboard,
  },
  {
    href: "/intelligence",
    title: "Analyze with AI",
    description: "Search by intent, brief repositories, compare projects, and find neighbors.",
    icon: Search,
  },
  {
    href: "/chatbot",
    title: "Ask the GitHub data",
    description: "Use a chat interface to query live GitHub AI trend data in plain language.",
    icon: BotMessageSquare,
  },
];

export default function OverviewPage() {
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const { data: categorySummary } = useCategorySummary();
  const { data: topicRotation } = useTopicRotation(7);

  const headlineStats = useMemo(() => {
    const summary = categorySummary ?? [];
    return {
      totalRepos: summary.reduce((acc, item) => acc + item.repo_count, 0),
      totalStars: summary.reduce((acc, item) => acc + item.total_stars, 0),
      weeklyDelta: summary.reduce((acc, item) => acc + item.weekly_star_delta, 0),
    };
  }, [categorySummary]);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 pb-10 sm:px-6">
        <section className="showcase-shell rounded-2xl border border-slate-200/90 px-5 py-7 sm:px-7 lg:px-8">
          <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_440px]">
            <div className="space-y-5">
              <div className="inline-flex rounded-full border border-sky-200/80 bg-white/85 px-3 py-1 text-[11px] font-semibold uppercase text-sky-800/75">
                Live GitHub AI market console
              </div>
              <div className="max-w-4xl space-y-3">
                <h1 className="text-3xl font-semibold text-slate-950 sm:text-5xl">
                  Track what AI builders are starring, shipping, and comparing now.
                </h1>
                <p className="max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
                  The app is now split into focused workspaces: overview for the market
                  pulse, dashboard for analysis, intelligence for AI workflows, and
                  chatbot for plain-language questions over GitHub trend data.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard label="Tracked repos" value={formatNumber(headlineStats.totalRepos)} />
                <MetricCard label="Aggregate stars" value={formatNumber(headlineStats.totalStars)} />
                <MetricCard
                  label="Weekly delta"
                  value={`+${formatNumber(headlineStats.weeklyDelta)}`}
                  valueClassName="text-emerald-600"
                />
              </div>
            </div>

            <div className="terminal-panel data-grid rounded-2xl p-5">
              <div className="section-kicker">Fastest Topics</div>
              <div className="mt-3 space-y-3">
                {(topicRotation ?? []).slice(0, 6).map((topic) => (
                  <div
                    key={topic.topic}
                    className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white/80 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-950">
                        {topic.topic}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {formatNumber(topic.repo_count)} repos in rotation
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-sm font-semibold text-emerald-600">
                      <TrendingUp className="h-4 w-4" />
                      +{formatNumber(topic.star_delta)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <Link
                key={action.href}
                href={action.href}
                className="group rounded-lg border border-slate-200 bg-white/86 p-5 shadow-[0_18px_42px_-34px_rgba(15,23,42,0.2)] transition-colors hover:border-sky-300 hover:bg-white"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-slate-950">{action.title}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      {action.description}
                    </p>
                  </div>
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sky-600 transition-colors group-hover:border-sky-200 group-hover:bg-sky-50">
                    <Icon className="h-5 w-5" />
                  </span>
                </div>
              </Link>
            );
          })}
        </section>

        <section className="space-y-4">
          <div>
            <div className="section-kicker">Market Snapshot</div>
            <h2 className="mt-1 text-2xl font-semibold text-slate-950">
              Category posture and the current week in review
            </h2>
          </div>
          <CategorySummaryGrid />
          <WeekInReview days={7} onSelectRepo={setSelectedRepo} />
          {selectedRepo && (
            <div className="rounded-lg border border-slate-200 bg-white/86 px-4 py-3 text-sm text-slate-600">
              Selected repo: <span className="font-medium text-slate-950">{selectedRepo}</span>.
              Open Intelligence to generate a repo brief or comparison.
            </div>
          )}
        </section>
      </main>

      <Footer />
    </div>
  );
}

function MetricCard({
  label,
  value,
  valueClassName = "text-slate-950",
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="showcase-panel rounded-lg p-4">
      <div className="section-kicker">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${valueClassName}`}>{value}</div>
    </div>
  );
}
