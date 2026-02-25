"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { BarChart2 } from "lucide-react";

import { useRepoTimeseries } from "@/hooks/useRepoTimeseries";
import { formatNumber } from "@/lib/utils";

interface Props {
  repoName: string | null;
  days: number;
}

function EmptyState() {
  return (
    <div className="flex h-full items-center justify-center text-muted-foreground">
      <div className="text-center">
        <BarChart2 className="mx-auto mb-2 h-8 w-8 opacity-40" />
        <p className="text-sm">Click a repository to view its star growth chart</p>
      </div>
    </div>
  );
}

export function StarGrowthChart({ repoName, days }: Props) {
  const { data, isLoading } = useRepoTimeseries(repoName, days);

  return (
    <div className="card-glow overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">
          {repoName ? (
            <>
              Star Growth —{" "}
              <span className="text-primary">{repoName}</span>
            </>
          ) : (
            "Star Growth"
          )}
        </h2>
        {repoName && (
          <span className="text-xs text-muted-foreground">last {days} days</span>
        )}
      </div>

      <div className="h-64 p-4">
        {!repoName ? (
          <EmptyState />
        ) : isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No data available for this period
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                opacity={0.5}
              />
              <XAxis
                dataKey="event_date"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: string) => {
                  const d = new Date(v);
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
              />
              <YAxis
                yAxisId="stars"
                orientation="left"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <YAxis
                yAxisId="events"
                orientation="right"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                formatter={(value: number, name: string) => [
                  formatNumber(value),
                  name === "star_count" ? "New Stars" : "Events",
                ]}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "hsl(var(--muted-foreground))" }}
                formatter={(value: string) =>
                  value === "star_count" ? "New Stars" : "Total Events"
                }
              />
              <Bar
                yAxisId="stars"
                dataKey="star_count"
                fill="#3b82f6"
                opacity={0.85}
                radius={[2, 2, 0, 0]}
              />
              <Line
                yAxisId="events"
                type="monotone"
                dataKey="total_events"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
