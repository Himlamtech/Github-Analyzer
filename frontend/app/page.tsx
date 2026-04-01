"use client";

import { useState } from "react";

import { Header } from "@/components/layout/Header";
import { AISearchPanel } from "@/components/ai/AISearchPanel";
import { CategoryFilter } from "@/components/dashboard/CategoryFilter";
import { CategorySummaryGrid } from "@/components/dashboard/CategorySummaryGrid";
import { TopReposTable } from "@/components/dashboard/TopReposTable";
import { TopicRotationBoard } from "@/components/dashboard/TopicRotationBoard";
import { WeekInReview } from "@/components/dashboard/WeekInReview";
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
        <section className="overflow-hidden rounded-3xl border border-border bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.14),_transparent_28%),linear-gradient(180deg,_rgba(15,23,42,0.06),_rgba(15,23,42,0.01))] px-5 py-6 sm:px-6">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_0.9fr] lg:items-end">
            <div className="space-y-3">
              <div className="inline-flex rounded-full border border-border bg-background/80 px-3 py-1 text-xs text-muted-foreground">
                market intelligence console
              </div>
              <div className="max-w-4xl text-3xl font-semibold tracking-tight sm:text-4xl">
                Keep the hard numbers compact, then make the movers impossible to miss.
              </div>
              <p className="max-w-3xl text-sm leading-6 text-muted-foreground sm:text-base">
                This layout prioritizes leaders, weekly risers, language concentration,
                and discovery search before deep drilldown. The goal is to turn stored
                data into a product surface that reads like market insight, not a raw dump.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <HeroStat
                label="Current window"
                value={`${days} days`}
                tone="sky"
              />
              <HeroStat
                label="Category filter"
                value={category === "all" ? "All AI" : category}
                tone="emerald"
              />
              <HeroStat
                label="Focus repo"
                value={selectedRepo ? selectedRepo.split("/")[1] : "None"}
                tone="violet"
              />
              <HeroStat
                label="Drilldown"
                value={selectedRepo ? "Active" : "Ready"}
                tone="amber"
              />
            </div>
          </div>
        </section>

        <CategoryFilter
          category={category}
          days={days}
          onCategoryChange={setCategory}
          onDaysChange={(d) => {
            setDays(d);
            setSelectedRepo(null);
          }}
        />

        <CategorySummaryGrid days={days} />
        <AISearchPanel
          category={category}
          days={days}
          onSelectRepo={setSelectedRepo}
        />
        <WeekInReview days={days} onSelectRepo={setSelectedRepo} />

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.35fr_0.95fr]">
          <TopReposTable
            category={category}
            days={days}
            selectedRepo={selectedRepo}
            onSelectRepo={setSelectedRepo}
          />
          <LanguageDistChart days={days} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TopicHeatmap days={days} />
          <TopicRotationBoard days={days} />
        </div>

        <StarGrowthChart repoName={selectedRepo} days={days} />
        {selectedRepo && <ActivityTimeline repoName={selectedRepo} days={days} />}
      </main>
    </div>
  );
}

function HeroStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "sky" | "emerald" | "violet" | "amber";
}) {
  const toneClasses = {
    sky: "border-sky-400/20 bg-sky-500/10 text-sky-100",
    emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
    violet: "border-violet-400/20 bg-violet-500/10 text-violet-100",
    amber: "border-amber-400/20 bg-amber-500/10 text-amber-100",
  };

  return (
    <div className={`rounded-2xl border p-4 ${toneClasses[tone]}`}>
      <div className="text-[11px] uppercase tracking-[0.18em] text-white/70">{label}</div>
      <div className="mt-2 truncate text-lg font-semibold text-foreground">{value}</div>
    </div>
  );
}
