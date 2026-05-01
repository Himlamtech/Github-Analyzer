"use client";

import { useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  BrainCircuit,
  GitCompareArrows,
  Layers3,
  Orbit,
  Sparkles,
} from "lucide-react";

import { AIMarketBriefCard } from "@/components/ai/AIMarketBriefCard";
import { AIRepoBriefCard } from "@/components/ai/AIRepoBriefCard";
import { AIRepoCompareCard } from "@/components/ai/AIRepoCompareCard";
import { AIRelatedReposCard } from "@/components/ai/AIRelatedReposCard";
import { AISearchPanel } from "@/components/ai/AISearchPanel";
import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { LanguageDistChart } from "@/components/dashboard/LanguageDistChart";
import { TopReposTable } from "@/components/dashboard/TopReposTable";
import { TopicHeatmap } from "@/components/dashboard/TopicHeatmap";
import { TopicRotationBoard } from "@/components/dashboard/TopicRotationBoard";
import { TrendingRepos } from "@/components/dashboard/TrendingRepos";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { useCategorySummary, useTopicRotation } from "@/hooks/useDashboard";
import { CATEGORY_LABELS, type Category } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type InsightDeckTab = "market" | "brief" | "compare" | "neighbors";

const INSIGHT_TABS: Array<{
  key: InsightDeckTab;
  label: string;
  icon: LucideIcon;
  description: string;
}> = [
  {
    key: "market",
    label: "Market Brief",
    icon: Layers3,
    description: "Weekly thesis across categories, breakouts, and themes.",
  },
  {
    key: "brief",
    label: "Repo Brief",
    icon: Sparkles,
    description: "Explain why the selected repository is moving now.",
  },
  {
    key: "compare",
    label: "Compare",
    icon: GitCompareArrows,
    description: "Put two repositories into the same operating frame.",
  },
  {
    key: "neighbors",
    label: "Related",
    icon: Orbit,
    description: "See nearby projects in the same demand cluster.",
  },
];

export default function DashboardPage() {
  const [category, setCategory] = useState<Category>("all");
  const [days, setDays] = useState(7);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [activeDeck, setActiveDeck] = useState<InsightDeckTab>("market");
  const { data: categorySummary } = useCategorySummary();
  const { data: topicRotation } = useTopicRotation(days);

  const activeCategoryLabel =
    category === "all" ? "All AI categories" : CATEGORY_LABELS[category] ?? category;

  const headlineStats = useMemo(() => {
    const summary = categorySummary ?? [];
    const totalRepos = summary.reduce((acc, item) => acc + item.repo_count, 0);
    const totalStars = summary.reduce((acc, item) => acc + item.total_stars, 0);
    const totalDelta = summary.reduce((acc, item) => acc + item.weekly_star_delta, 0);

    return { totalRepos, totalStars, totalDelta };
  }, [categorySummary]);

  function renderInsightDeck() {
    switch (activeDeck) {
      case "brief":
        return <AIRepoBriefCard repoName={selectedRepo} days={days} />;
      case "compare":
        return <AIRepoCompareCard baseRepoName={selectedRepo} days={days} />;
      case "neighbors":
        return (
          <AIRelatedReposCard
            repoName={selectedRepo}
            days={days}
            onSelectRepo={setSelectedRepo}
          />
        );
      case "market":
      default:
        return <AIMarketBriefCard days={days} onSelectRepo={setSelectedRepo} />;
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header
        days={days}
        categoryLabel={activeCategoryLabel}
        selectedRepo={selectedRepo}
      />

      <main className="mx-auto max-w-screen-2xl space-y-8 px-4 pb-10 sm:px-6">
        <section
          id="pulse"
          className="showcase-shell rounded-[32px] border border-slate-200/90 px-5 py-6 sm:px-6 sm:py-7"
        >
          <div className="relative z-10 space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-sky-200/80 bg-white/85 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-800/75">
                Live GitHub AI landscape
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50/90 px-3 py-1 text-xs text-slate-600">
                Window: {days} days
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50/90 px-3 py-1 text-xs text-slate-600">
                {activeCategoryLabel}
              </span>
            </div>

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_380px]">
              <div className="space-y-4">
                <div className="max-w-5xl space-y-3">
                  <h1 className="max-w-4xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl xl:text-[3.15rem] xl:leading-[1.04]">
                    GitHub AI Trend Analyzer helps you discover what is breaking out,
                    what people are building with, and which repositories deserve
                    attention this week.
                  </h1>
                  <p className="max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
                    Start with the market introduction, search by intent, scan the
                    hottest topics this week, then move into star leaders, weekly
                    gainers, ecosystem charts, and AI analysis.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="section-kicker">Tracked Repos</div>
                    <div className="mt-2 text-2xl font-semibold text-slate-950">
                      {formatNumber(headlineStats.totalRepos)}
                    </div>
                  </div>
                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="section-kicker">Aggregate Stars</div>
                    <div className="mt-2 text-2xl font-semibold text-slate-950">
                      {formatNumber(headlineStats.totalStars)}
                    </div>
                  </div>
                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="section-kicker">Weekly Delta</div>
                    <div className="mt-2 text-2xl font-semibold text-emerald-600">
                      +{formatNumber(headlineStats.totalDelta)}
                    </div>
                  </div>
                </div>

                <div className="showcase-panel rounded-[26px] p-4">
                  <CategoryFilter
                    category={category}
                    days={days}
                    onCategoryChange={setCategory}
                    onDaysChange={(nextDays) => {
                      setDays(nextDays);
                      setSelectedRepo(null);
                    }}
                  />
                </div>

                <div className="showcase-panel rounded-[26px] p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-2">
                      <div className="section-kicker">AI Workflow</div>
                      <h2 className="text-xl font-semibold tracking-tight text-slate-950">
                        Search once, then keep the same repo active across the AI deck.
                      </h2>
                      <p className="max-w-2xl text-sm leading-6 text-slate-600">
                        Pick a repository from natural-language search, then jump into
                        repo brief, comparison, related projects, and market context
                        without losing the current selection.
                      </p>
                    </div>

                    <a
                      href="#intelligence"
                      className="inline-flex items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                    >
                      Open AI deck
                    </a>
                  </div>
                </div>

                <div className="rounded-[28px] border border-slate-200/85 bg-white/84 p-1 shadow-[0_22px_50px_-34px_rgba(15,23,42,0.24)]">
                  <AISearchPanel
                    category={category}
                    days={days}
                    onSelectRepo={setSelectedRepo}
                  />
                </div>
              </div>

              <aside className="showcase-spotlight rounded-[28px] p-5 text-white">
                <div className="relative z-10 space-y-5">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-100/78">
                      Hot topics this week
                    </div>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                      Topics rotating fastest right now
                    </h2>
                    <p className="mt-3 text-sm leading-6 text-sky-100/76">
                      These are the tags gaining the most star activity compared with
                      the prior matching window.
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {(topicRotation ?? []).slice(0, 8).map((item) => (
                      <span
                        key={item.topic}
                        className="rounded-full border border-white/12 bg-white/10 px-3 py-1.5 text-xs text-sky-50"
                      >
                        {item.topic} <span className="text-cyan-200">+{formatNumber(item.star_delta)}</span>
                      </span>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-white/12 bg-white/8">
                    <TopicRotationBoard days={days} />
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section id="movement" className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Repositories</div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                Top stars now and strongest weekly gainers
              </h2>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              The first repo block separates market size from market acceleration:
              long-term star leaders on the left, weekly momentum winners on the right.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.18fr)_360px]">
            <TopReposTable
              category={category}
              days={days}
              selectedRepo={selectedRepo}
              onSelectRepo={setSelectedRepo}
              limit={10}
              sortBy="stargazers_count"
              source="top-starred-repos"
              title="Top 10 Repositories By Total Stars"
              subtitle="Current star leaders surfaced from the live dashboard set"
            />

            <TrendingRepos days={days} onSelectRepo={setSelectedRepo} />
          </div>
        </section>

        <section id="ecosystem" className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Charts</div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                Languages and tech stacks used across active repositories
              </h2>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              This section focuses only on the ecosystem composition: programming
              languages on one side and topic or stack concentration on the other.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <LanguageDistChart days={days} />
            <TopicHeatmap days={days} />
          </div>
        </section>

        <section id="intelligence" className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">AI Analyze</div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                AI explanations, comparisons, and repo intelligence
              </h2>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              The AI section stays at the end of the page. Use it after you already
              know which topic and repository deserve deeper analysis.
            </p>
          </div>

          <div className="showcase-shell rounded-[32px] border border-slate-200/90 px-5 py-6 sm:px-6">
            <div className="relative z-10 space-y-5">
              <div className="grid gap-2 lg:grid-cols-5">
                {INSIGHT_TABS.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeDeck === tab.key;

                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveDeck(tab.key)}
                      className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                        isActive
                          ? "border-sky-300/90 bg-white text-slate-900 shadow-[0_16px_36px_-28px_rgba(37,99,235,0.45)]"
                          : "border-slate-200/80 bg-white/66 text-slate-600 hover:bg-white/88"
                      }`}
                    >
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-sky-500"}`} />
                        {tab.label}
                      </div>
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {tab.description}
                      </p>
                    </button>
                  );
                })}
              </div>

              <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
                <aside className="terminal-panel data-grid rounded-[28px] p-5">
                  <div className="space-y-5">
                    <div>
                      <div className="section-kicker">Selected Repo</div>
                      <div className="mt-2 text-xl font-semibold text-slate-950">
                        {selectedRepo ?? "No repository selected"}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Click any repo from the two leaderboard blocks or from search to
                        keep the same repository active across all AI panels.
                      </p>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-white/82 p-4">
                      <div className="section-kicker">Suggested Flow</div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Search first, pick a repo, then generate a market brief, repo
                        brief, compare view, or related-repo map.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <button
                        onClick={() => setActiveDeck("market")}
                        className="w-full rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                      >
                        Open market brief
                      </button>
                      <button
                        onClick={() => {
                          if (selectedRepo) {
                            setActiveDeck("brief");
                            return;
                          }
                          document
                            .getElementById("pulse")
                            ?.scrollIntoView({ behavior: "smooth", block: "start" });
                        }}
                        className="w-full rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                      >
                        {selectedRepo ? "Explain selected repo" : "Pick from AI search above"}
                      </button>
                      <button
                        onClick={() => setActiveDeck("compare")}
                        className="w-full rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
                      >
                        Compare repositories
                      </button>
                    </div>
                  </div>
                </aside>

                <div className="rounded-[28px] border border-slate-200/85 bg-white/84 p-1 shadow-[0_22px_50px_-34px_rgba(15,23,42,0.24)]">
                  {renderInsightDeck()}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
