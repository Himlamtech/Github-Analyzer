"use client";

import { useState } from "react";

import { Header } from "@/components/layout/Header";
import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { CategorySummaryGrid } from "@/components/dashboard/CategorySummaryGrid";
import { TopReposTable } from "@/components/dashboard/TopReposTable";
import { TrendingRepos } from "@/components/dashboard/TrendingRepos";
import { StarGrowthChart } from "@/components/dashboard/StarGrowthChart";
import { TopicHeatmap } from "@/components/dashboard/TopicHeatmap";
import { LanguageDistChart } from "@/components/dashboard/LanguageDistChart";
import { ActivityTimeline } from "@/components/dashboard/ActivityTimeline";
import type { Category } from "@/lib/types";

export default function DashboardPage() {
  const [category, setCategory] = useState<Category>("all");
  const [days, setDays] = useState(7);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="mx-auto max-w-screen-2xl space-y-5 px-4 py-5 sm:px-6">
        {/* Row 1: Filters */}
        <CategoryFilter
          category={category}
          days={days}
          onCategoryChange={setCategory}
          onDaysChange={(d) => {
            setDays(d);
            setSelectedRepo(null);
          }}
        />

        {/* Row 2: Category summary cards */}
        <CategorySummaryGrid />

        {/* Row 3: Top repos table + Trending */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <TopReposTable
              category={category}
              days={days}
              selectedRepo={selectedRepo}
              onSelectRepo={setSelectedRepo}
            />
          </div>
          <div className="lg:col-span-2">
            <TrendingRepos days={days} onSelectRepo={setSelectedRepo} />
          </div>
        </div>

        {/* Row 4: Star growth chart (shown when a repo is selected) */}
        <StarGrowthChart repoName={selectedRepo} days={days} />

        {/* Row 5: Activity timeline (shown when a repo is selected) */}
        {selectedRepo && (
          <ActivityTimeline repoName={selectedRepo} days={days} />
        )}

        {/* Row 6: Topic heatmap + Language distribution */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TopicHeatmap days={days} />
          <LanguageDistChart days={days} />
        </div>
      </main>
    </div>
  );
}
