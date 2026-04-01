"use client";

import { useCategorySummary } from "@/hooks/useDashboard";
import { cn } from "@/lib/utils";
import { CATEGORY_COLORS, CATEGORY_LABELS, type Category } from "@/lib/types";

const FALLBACK_CATEGORIES: Category[] = [
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
  const { data } = useCategorySummary(days);
  const dynamicCategories = (data ?? []).map((item) => item.category);
  const categories = [
    "all",
    ...new Set([...dynamicCategories, ...FALLBACK_CATEGORIES.filter((item) => item !== "all")]),
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {/* Category pills */}
      <div className="flex flex-wrap gap-1.5">
        {categories.map((cat) => {
          const isActive = category === cat;
          const color = cat === "all" ? "#3b82f6" : CATEGORY_COLORS[cat] ?? "#6b7280";
          const label =
            cat === "all" ? "All Categories" : CATEGORY_LABELS[cat] ?? cat;

          return (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-all",
                isActive
                  ? "border-transparent text-white shadow-sm"
                  : "border-border bg-transparent text-muted-foreground hover:text-foreground",
              )}
              style={isActive ? { backgroundColor: color, borderColor: color } : {}}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Days selector */}
      <div className="flex items-center gap-1 rounded-lg border border-border bg-muted p-0.5">
        {DAYS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onDaysChange(opt.value)}
            className={cn(
              "rounded px-2.5 py-1 text-xs font-medium transition-all",
              days === opt.value
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
