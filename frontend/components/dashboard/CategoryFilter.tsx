"use client";

import { cn } from "@/lib/utils";
import { CATEGORY_COLORS, CATEGORY_LABELS, type Category } from "@/lib/types";

const CATEGORIES: Category[] = [
  "all",
  "LLM",
  "Agent",
  "Diffusion",
  "Multimodal",
  "DataEng",
  "Other",
];

const DAYS_OPTIONS = [
  { label: "7d", value: 7 },
  { label: "14d", value: 14 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

interface Props {
  category: Category;
  days: number;
  onCategoryChange: (c: Category) => void;
  onDaysChange: (d: number) => void;
}

export function CategoryFilter({
  category,
  days,
  onCategoryChange,
  onDaysChange,
}: Props) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-800/70">
          Category filter
        </div>
        <div className="flex flex-wrap gap-1.5">
        {CATEGORIES.map((cat) => {
          const isActive = category === cat;
          const color = cat === "all" ? "#3b82f6" : CATEGORY_COLORS[cat] ?? "#6b7280";
          const label =
            cat === "all" ? "All Categories" : CATEGORY_LABELS[cat] ?? cat;

          return (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
                isActive
                  ? "border-transparent text-white shadow-sm"
                  : "border-slate-200 bg-white/85 text-slate-600 hover:text-slate-950",
              )}
              style={isActive ? { backgroundColor: color, borderColor: color } : {}}
            >
              {label}
            </button>
          );
        })}
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-800/70">
          Supporting window
        </div>
        <div className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-slate-50/85 p-1">
          {DAYS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onDaysChange(opt.value)}
              className={cn(
                "rounded-xl px-3 py-1.5 text-xs font-medium transition-all",
                days === opt.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-slate-600 hover:bg-white hover:text-slate-950",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
