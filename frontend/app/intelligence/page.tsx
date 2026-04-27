"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { GitCompareArrows, Layers3, Orbit, Sparkles } from "lucide-react";

import { AIMarketBriefCard } from "@/components/ai/AIMarketBriefCard";
import { AIRepoBriefCard } from "@/components/ai/AIRepoBriefCard";
import { AIRepoCompareCard } from "@/components/ai/AIRepoCompareCard";
import { AIRelatedReposCard } from "@/components/ai/AIRelatedReposCard";
import { AISearchPanel } from "@/components/ai/AISearchPanel";
import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { type Category } from "@/lib/types";

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

export default function IntelligencePage() {
  const [category, setCategory] = useState<Category>("all");
  const [days, setDays] = useState(7);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [activeDeck, setActiveDeck] = useState<InsightDeckTab>("market");

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
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-8 px-4 pb-10 sm:px-6">
        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Intelligence</div>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                Search, brief, compare, and map GitHub AI repos
              </h1>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Pick a repository once, then keep it active across all AI analysis
              panels without losing your current filter context.
            </p>
          </div>

          <div className="showcase-panel rounded-2xl p-4">
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
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-slate-200/85 bg-white/84 p-1 shadow-[0_22px_50px_-34px_rgba(15,23,42,0.24)]">
            <AISearchPanel
              category={category}
              days={days}
              onSelectRepo={(repoName) => {
                setSelectedRepo(repoName);
                setActiveDeck("brief");
              }}
            />
          </div>

          <aside className="terminal-panel data-grid rounded-2xl p-5">
            <div className="section-kicker">Selected Repo</div>
            <div className="mt-2 text-xl font-semibold text-slate-950">
              {selectedRepo ?? "No repository selected"}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Search by use case, pick a repo, then generate focused AI context from
              the same selection.
            </p>
            <div className="mt-5 grid gap-2">
              <button
                onClick={() => setActiveDeck("market")}
                className="rounded-lg border border-slate-200 bg-white/82 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
              >
                Open market brief
              </button>
              <button
                onClick={() => setActiveDeck("brief")}
                className="rounded-lg border border-slate-200 bg-white/82 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
              >
                Explain selected repo
              </button>
              <button
                onClick={() => setActiveDeck("compare")}
                className="rounded-lg border border-slate-200 bg-white/82 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-white"
              >
                Compare repositories
              </button>
            </div>
          </aside>
        </section>

        <section className="space-y-4">
          <div className="grid gap-2 md:grid-cols-4">
            {INSIGHT_TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeDeck === tab.key;

              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveDeck(tab.key)}
                  className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                    isActive
                      ? "border-sky-300/90 bg-white text-slate-900 shadow-[0_16px_36px_-28px_rgba(37,99,235,0.45)]"
                      : "border-slate-200/80 bg-white/70 text-slate-600 hover:bg-white"
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

          <div className="rounded-lg border border-slate-200/85 bg-white/84 p-1 shadow-[0_22px_50px_-34px_rgba(15,23,42,0.24)]">
            {renderInsightDeck()}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
