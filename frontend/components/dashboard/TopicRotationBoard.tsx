"use client";

import { Repeat2 } from "lucide-react";

import { useTopicRotation } from "@/hooks/useDashboard";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
}

export function TopicRotationBoard({ days }: Props) {
  const { data, error, isLoading } = useTopicRotation(days);

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Repeat2 className="h-4 w-4 text-emerald-300" />
        <h2 className="text-sm font-semibold">Topic Rotation</h2>
        <span className="ml-auto text-xs text-muted-foreground">vs prior {days}d</span>
      </div>

      <div className="divide-y divide-border/60">
        {isLoading &&
          Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="animate-pulse px-4 py-3">
              <div className="mb-2 h-4 w-32 rounded bg-muted" />
              <div className="h-3 w-full rounded bg-muted" />
            </div>
          ))}

        {!isLoading &&
          (data ?? []).map((topic) => {
            const width = Math.max(
              12,
              Math.min(
                100,
                topic.current_star_count === 0
                  ? 12
                  : Math.round((topic.star_delta / topic.current_star_count) * 100),
              ),
            );

            return (
              <div key={topic.topic} className="px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{topic.topic}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {formatNumber(topic.repo_count)} repos · {formatNumber(topic.previous_star_count)}{" "}
                      previous stars
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-emerald-300">
                      +{formatNumber(topic.star_delta)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatNumber(topic.current_star_count)} current stars
                    </div>
                  </div>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-emerald-400"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })}

        {!isLoading && error && (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            Topic rotation is unavailable until the dashboard API route is reachable.
          </div>
        )}

        {!isLoading && !error && (data?.length ?? 0) === 0 && (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            No topics gained enough new star activity in the current window.
          </div>
        )}
      </div>
    </section>
  );
}
