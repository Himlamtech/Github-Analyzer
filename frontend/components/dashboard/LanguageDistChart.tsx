"use client";

import { Code2 } from "lucide-react";

import { useLanguageBreakdown } from "@/hooks/useDashboard";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
}

const LANG_COLORS = [
  "#2563eb",
  "#0f766e",
  "#7c3aed",
  "#d97706",
  "#db2777",
  "#0891b2",
];

export function LanguageDistChart({ days }: Props) {
  const { data, isLoading } = useLanguageBreakdown(days);
  const languages = (data ?? []).slice(0, 20);
  const total = languages.reduce((acc, item) => acc + item.star_count, 0);
  const maxValue = Math.max(...languages.map((item) => item.star_count), 1);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 px-4 py-4 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Code2 className="h-4 w-4 text-emerald-300" />
              Top 20 Languages
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Language concentration by stars observed in the selected window.
            </p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <div>last {days}d</div>
            <div>{formatNumber(total)} stars tracked</div>
          </div>
        </div>
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="animate-pulse rounded-2xl border border-border bg-background/60 p-3">
                <div className="mb-2 h-4 w-28 rounded bg-muted" />
                <div className="h-2 w-full rounded-full bg-muted" />
              </div>
            ))}
          </div>
        ) : languages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-background/70 px-4 py-8 text-sm text-muted-foreground">
            No language data available for this window.
          </div>
        ) : (
          languages.map((item, index) => {
            const width = Math.max(
              8,
              Math.round((item.star_count / maxValue) * 100),
            );
            const color = LANG_COLORS[index % LANG_COLORS.length];
            const share =
              total === 0 ? 0 : Math.round((item.star_count / total) * 100);

            return (
              <div
                key={item.language}
                className="rounded-2xl border border-border bg-background/60 p-3"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="w-6 shrink-0 text-center text-xs font-bold text-muted-foreground">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">
                        {item.language || "Unknown"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatNumber(item.repo_count)} repos
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">
                      {formatNumber(item.star_count)}
                    </div>
                    <div className="text-xs text-muted-foreground">{share}% share</div>
                  </div>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${width}%`, backgroundColor: color }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
