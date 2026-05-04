"use client";

import { useState } from "react";

import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { CategorySummaryGrid } from "@/components/dashboard/CategorySummaryGrid";
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
  const [historyLimit, setHistoryLimit] = useState(10);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const historyLimitOptions = [5, 10, 20];

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-8 px-4 pb-10 sm:px-6">
        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Dashboard</div>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
                GitHub leaders, weekly movers, and ecosystem shape
              </h1>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Start with two primary leaderboards: all-time repositories by stars
              and the repos adding the most stars in the current GMT+7 week.
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

        <section id="main-dashboards" className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="section-kicker">Main Dashboards</div>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                Historical stars and current-week growth
              </h2>
            </div>
            <div className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-slate-50/85 p-1">
              {historyLimitOptions.map((limit) => (
                <button
                  key={limit}
                  onClick={() => setHistoryLimit(limit)}
                  className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                    historyLimit === limit
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-slate-600 hover:bg-white hover:text-slate-950"
                  }`}
                >
                  Top {limit}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_420px]">
            <TopReposTable
              category={category}
              days={days}
              selectedRepo={selectedRepo}
              onSelectRepo={setSelectedRepo}
              limit={historyLimit}
              sortBy="stargazers_count"
              source="top-starred-repos"
              showWindowStars={false}
              timeLabel="all-time"
              title="Top repositories by all-time stars"
              subtitle="Historical leaders ranked by current GitHub star count"
            />
            <TrendingRepos days={days} limit={10} onSelectRepo={setSelectedRepo} />
          </div>
        </section>

        <section id="supporting-dashboards" className="space-y-4">
          <div>
            <div className="section-kicker">Supporting Dashboards</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
              Languages, categories, topics, and external signal
            </h2>
          </div>

          <WeekInReview days={days} onSelectRepo={setSelectedRepo} />

          <div className="grid gap-4 xl:grid-cols-2">
            <NewsRadarPanel days={days} onSelectRepo={setSelectedRepo} />
            <TopicRotationBoard days={days} />
          </div>
        </section>

        <section id="ecosystem" className="space-y-4">
          <div>
            <div className="section-kicker">Ecosystem</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
              Ranking by language, category, and topic concentration
            </h2>
          </div>

          <CategorySummaryGrid />

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
