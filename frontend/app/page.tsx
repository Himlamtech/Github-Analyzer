"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowUpRight,
  BrainCircuit,
  GitCompareArrows,
  Layers3,
  LineChart,
  Orbit,
  Search,
  Sparkles,
} from "lucide-react";

import { Header } from "@/components/layout/Header";
import { AIMarketBriefCard } from "@/components/ai/AIMarketBriefCard";
import { AIRepoCompareCard } from "@/components/ai/AIRepoCompareCard";
import { AIRelatedReposCard } from "@/components/ai/AIRelatedReposCard";
import { AISearchPanel } from "@/components/ai/AISearchPanel";
import { AIRepoBriefCard } from "@/components/ai/AIRepoBriefCard";
import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { CategorySummaryGrid } from "@/components/dashboard/CategorySummaryGrid";
import { NewsRadarPanel } from "@/components/dashboard/NewsRadarPanel";
import { TopicRotationBoard } from "@/components/dashboard/TopicRotationBoard";
import { TopReposTable } from "@/components/dashboard/TopReposTable";
import { TrendingRepos } from "@/components/dashboard/TrendingRepos";
import { WeekInReview } from "@/components/dashboard/WeekInReview";
import { StarGrowthChart } from "@/components/dashboard/StarGrowthChart";
import { TopicHeatmap } from "@/components/dashboard/TopicHeatmap";
import { LanguageDistChart } from "@/components/dashboard/LanguageDistChart";
import { ActivityTimeline } from "@/components/dashboard/ActivityTimeline";
import { CATEGORY_LABELS, type Category } from "@/lib/types";

type InsightDeckTab = "search" | "market" | "brief" | "compare" | "neighbors";

const INSIGHT_TABS: Array<{
  key: InsightDeckTab;
  label: string;
  icon: LucideIcon;
  description: string;
}> = [
  {
    key: "search",
    label: "Discovery Search",
    icon: Search,
    description: "Find emerging repos by intent and capability.",
  },
  {
    key: "market",
    label: "Market Brief",
    icon: Layers3,
    description: "Generate the weekly narrative for the whole market.",
  },
  {
    key: "brief",
    label: "Repo Brief",
    icon: Sparkles,
    description: "Explain why the selected repo matters right now.",
  },
  {
    key: "compare",
    label: "Compare",
    icon: GitCompareArrows,
    description: "Put two repos side by side and expose tradeoffs.",
  },
  {
    key: "neighbors",
    label: "Ecosystem",
    icon: Orbit,
    description: "Surface nearby projects in the same momentum cluster.",
  },
];

export default function DashboardPage() {
  const [category, setCategory] = useState<Category>("all");
  const [days, setDays] = useState(7);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [activeDeck, setActiveDeck] = useState<InsightDeckTab>("search");

  const activeCategoryLabel =
    category === "all" ? "All categories" : CATEGORY_LABELS[category] ?? category;
  const hasSelection = selectedRepo !== null;

  function renderInsightDeck() {
    switch (activeDeck) {
      case "market":
        return <AIMarketBriefCard days={days} onSelectRepo={setSelectedRepo} />;
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
      case "search":
      default:
        return (
          <AISearchPanel
            category={category}
            days={days}
            onSelectRepo={setSelectedRepo}
          />
        );
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-8 px-4 pb-10 sm:px-6">
        <section className="showcase-shell rounded-[32px] border border-sky-200/75 px-5 py-6 sm:px-6 sm:py-7">
          <div className="relative z-10 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_360px]">
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-700/80">
                <span className="rounded-full border border-sky-200/80 bg-white/70 px-3 py-1 shadow-sm">
                  AI market pulse
                </span>
                <span className="rounded-full border border-cyan-200/80 bg-cyan-50/70 px-3 py-1 shadow-sm">
                  {days} day window
                </span>
                <span className="rounded-full border border-blue-200/80 bg-blue-50/70 px-3 py-1 shadow-sm">
                  {activeCategoryLabel}
                </span>
              </div>

              <div className="max-w-4xl space-y-3">
                <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl xl:text-[3.25rem] xl:leading-[1.05]">
                  Turn raw GitHub exhaust into a market story people can read in seconds.
                </h1>
                <p className="max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
                  This landing page now starts from change, momentum, and external
                  attention. The viewer sees what moved, why it matters, and where to
                  drill deeper without scrolling through a wall of disconnected cards.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="showcase-panel rounded-2xl p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/70">
                    Signal Stack
                  </div>
                  <div className="mt-2 text-lg font-semibold text-slate-900">
                    Movers, headlines, and repo narratives
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Start from the strongest shifts, then open the exact repo story that
                    explains them.
                  </p>
                </div>

                <div className="showcase-panel rounded-2xl p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/70">
                    Demo Shape
                  </div>
                  <div className="mt-2 text-lg font-semibold text-slate-900">
                    Shorter scroll, clearer sections
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    The page is grouped into showcase scenes instead of one long
                    operational dashboard.
                  </p>
                </div>

                <div className="showcase-panel rounded-2xl p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/70">
                    Background Art
                  </div>
                  <div className="mt-2 text-lg font-semibold text-slate-900">
                    Layered gradients and grid atmospherics
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Built to feel like a product showcase, not a plain admin surface.
                  </p>
                </div>
              </div>

              <div className="showcase-panel rounded-[26px] p-3">
                <CategoryFilter
                  category={category}
                  days={days}
                  onCategoryChange={setCategory}
                  onDaysChange={(d) => {
                    setDays(d);
                    setSelectedRepo(null);
                  }}
                />
              </div>
            </div>

            <aside className="showcase-spotlight rounded-[28px] p-5 text-white">
              <div className="relative z-10 flex h-full flex-col justify-between gap-5">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-sky-100/80">
                    <BrainCircuit className="h-4 w-4" />
                    Operator Deck
                  </div>

                  <div>
                    <div className="text-sm text-sky-100/75">Selected repository</div>
                    <div className="mt-2 text-2xl font-semibold tracking-tight">
                      {selectedRepo ?? "Choose a repo from the pulse below"}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-sky-100/78">
                      Use the command deck to pivot between discovery, market narrative,
                      repo explanation, comparison, and ecosystem context.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <button
                    onClick={() => setActiveDeck(hasSelection ? "brief" : "search")}
                    className="flex w-full items-center justify-between rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-left transition-colors hover:bg-white/16"
                  >
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] text-sky-100/70">
                        Next step
                      </div>
                      <div className="mt-1 text-sm font-medium">
                        {hasSelection ? "Open repo brief" : "Open discovery search"}
                      </div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-sky-100/80" />
                  </button>

                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
                    {INSIGHT_TABS.slice(0, 4).map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.key}
                          onClick={() => setActiveDeck(tab.key)}
                          className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                            activeDeck === tab.key
                              ? "border-cyan-300/40 bg-cyan-300/18"
                              : "border-white/12 bg-white/6 hover:bg-white/12"
                          }`}
                        >
                          <div className="flex items-center gap-2 text-sm font-medium">
                            <Icon className="h-4 w-4 text-cyan-200" />
                            {tab.label}
                          </div>
                          <p className="mt-1 text-xs leading-5 text-sky-100/70">
                            {tab.description}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700/75">
                Market Pulse
              </div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                Open with the changes everyone should notice first
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-slate-600">
              The first fold is now editorial: biggest movers, external noise, and topic
              rotation share the same story instead of living in separate parts of the page.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]">
            <div className="space-y-4">
              <WeekInReview days={days} onSelectRepo={setSelectedRepo} />
              <NewsRadarPanel days={days} onSelectRepo={setSelectedRepo} />
            </div>

            <div className="space-y-4">
              <div className="showcase-shell rounded-[28px] border border-sky-200/75 p-4">
                <div className="relative z-10">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700/75">
                        Atlas
                      </div>
                      <div className="mt-1 text-lg font-semibold text-slate-900">
                        Category footprint
                      </div>
                    </div>
                    <div className="rounded-full border border-sky-200/80 bg-white/70 px-3 py-1 text-xs text-slate-500">
                      snapshot
                    </div>
                  </div>
                  <CategorySummaryGrid />
                </div>
              </div>
              <TopicRotationBoard days={days} />
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700/75">
                Leaderboards
              </div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                Keep the hard numbers compact and easy to scan
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-slate-600">
              Rankings and distributions stay visible, but they now live inside one
              analytics band instead of stretching the dashboard downward.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
            <TopReposTable
              category={category}
              days={days}
              selectedRepo={selectedRepo}
              onSelectRepo={setSelectedRepo}
            />

            <div className="space-y-4">
              <div className="showcase-shell rounded-[28px] border border-sky-200/75 p-5">
                <div className="relative z-10 space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700/75">
                        Selection Lens
                      </div>
                      <div className="mt-1 text-lg font-semibold text-slate-900">
                        One click should open a deeper story
                      </div>
                    </div>
                    <LineChart className="h-5 w-5 text-sky-500" />
                  </div>

                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/75">
                      Active focus
                    </div>
                    <div className="mt-2 text-xl font-semibold text-slate-900">
                      {selectedRepo ?? "No repository selected yet"}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      {selectedRepo
                        ? "Open the command deck below to generate a repo brief, compare it, or explore its neighbors."
                        : "Pick any repo from the movers or leaderboards and the lower deck will switch from market mode to repo mode."}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        onClick={() => setActiveDeck(selectedRepo ? "brief" : "search")}
                        className="rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
                      >
                        {selectedRepo ? "Open Repo Brief" : "Open Discovery Search"}
                      </button>
                      <button
                        onClick={() => setActiveDeck("compare")}
                        className="rounded-full border border-sky-200/80 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-sky-50"
                      >
                        Compare Repos
                      </button>
                    </div>
                  </div>

                  <TrendingRepos days={days} onSelectRepo={setSelectedRepo} />
                </div>
              </div>

              <LanguageDistChart days={days} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
            <TopicHeatmap days={days} />
            <div className="showcase-shell rounded-[28px] border border-sky-200/75 p-5">
              <div className="relative z-10 flex h-full flex-col justify-between gap-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-700/75">
                    Visual Rhythm
                  </div>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-900">
                    The dashboard now alternates narrative blocks and analytics blocks
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    That keeps the page readable during a demo and makes each section feel
                    intentional instead of stacked.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/75">
                      Narrative first
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      Movers and headlines frame the story before the user reaches dense
                      tables and charts.
                    </p>
                  </div>
                  <div className="showcase-panel rounded-2xl p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700/75">
                      Deep dive second
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      One selected repo can then unlock its own AI brief, compare view,
                      growth chart, and activity line.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="showcase-shell rounded-[32px] border border-sky-200/75 px-5 py-6 sm:px-6">
          <div className="relative z-10 space-y-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700/75">
                  AI Command Deck
                </div>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                  Keep the powerful tools, but surface them one at a time
                </h2>
              </div>
              <p className="max-w-2xl text-sm leading-6 text-slate-600">
                The deck condenses the AI features into a single premium panel. That
                keeps the page short while still letting you demonstrate search, market
                narrative, repo explanation, comparison, and ecosystem discovery.
              </p>
            </div>

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
                        : "border-sky-200/70 bg-white/58 text-slate-600 hover:bg-white/82"
                    }`}
                  >
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-sky-500"}`} />
                      {tab.label}
                    </div>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{tab.description}</p>
                  </button>
                );
              })}
            </div>

            <div className="rounded-[28px] border border-sky-200/75 bg-white/72 p-1 shadow-[0_22px_50px_-34px_rgba(37,99,235,0.28)]">
              {renderInsightDeck()}
            </div>
          </div>
        </section>

        {selectedRepo && (
          <section className="space-y-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700/75">
                Repo Deep Dive
              </div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                {selectedRepo}
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
              <StarGrowthChart repoName={selectedRepo} days={days} />
              <ActivityTimeline repoName={selectedRepo} days={days} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
