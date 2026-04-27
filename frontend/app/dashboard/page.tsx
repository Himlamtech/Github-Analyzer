"use client";

import { useState } from "react";

import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { LanguageDistChart } from "@/components/dashboard/LanguageDistChart";
import { NewsRadarPanel } from "@/components/dashboard/NewsRadarPanel";
import { TopicHeatmap } from "@/components/dashboard/TopicHeatmap";
import { TopicRotationBoard } from "@/components/dashboard/TopicRotationBoard";
import { TrendingRepos } from "@/components/dashboard/TrendingRepos";
import { TopReposTable } from "@/components/dashboard/TopReposTable";
import { WeekInReview } from "@/components/dashboard/WeekInReview";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { type Category } from "@/lib/types";

export default function DashboardPage() {
  const [category, setCategory] = useState<Category>("all");
  const [days, setDays] = useState(7);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-8 px-4 pb-10 sm:px-6">
        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Dashboard</div>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                Market pulse, movers, and ecosystem shape
              </h1>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Use this workspace for scanning weekly movement, comparing categories,
              and picking a repo to inspect later in Intelligence.
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

        <section id="pulse" className="space-y-4">
          <div>
            <div className="section-kicker">Pulse</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
              This week changed
            </h2>
          </div>
          <WeekInReview days={days} onSelectRepo={setSelectedRepo} />
        </section>

        <section id="movement" className="space-y-4">
          <div>
            <div className="section-kicker">Movement</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
              Top repos, trending repos, and external signal
            </h2>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]">
            <TopReposTable
              category={category}
              days={days}
              selectedRepo={selectedRepo}
              onSelectRepo={setSelectedRepo}
              limit={10}
              sortBy="stargazers_count"
              source="top-starred-repos"
              title="Top repositories by total stars"
              subtitle="Current market leaders with category context"
            />
            <TrendingRepos days={days} onSelectRepo={setSelectedRepo} />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <NewsRadarPanel days={days} onSelectRepo={setSelectedRepo} />
            <TopicRotationBoard days={days} />
          </div>
        </section>

        <section id="ecosystem" className="space-y-4">
          <div>
            <div className="section-kicker">Ecosystem</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
              Languages and topic concentration
            </h2>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <LanguageDistChart days={days} />
            <TopicHeatmap days={days} />
          </div>
        </section>

        {selectedRepo && (
          <div className="rounded-lg border border-slate-200 bg-white/86 px-4 py-3 text-sm text-slate-600">
            Selected repo: <span className="font-medium text-slate-950">{selectedRepo}</span>.
            Move to Intelligence to generate a brief or compare view.
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
