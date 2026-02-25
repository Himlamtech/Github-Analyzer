"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { useRepoTimeseries } from "@/hooks/useRepoTimeseries";
import { formatNumber } from "@/lib/utils";

interface Props {
  repoName: string | null;
  days: number;
}

export function ActivityTimeline({ repoName, days }: Props) {
  const { data, isLoading } = useRepoTimeseries(repoName, days);

  if (!repoName) return null;

  return (
    <div className="card-glow overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">
          Activity Timeline —{" "}
          <span className="text-primary">{repoName}</span>
        </h2>
        <span className="text-xs text-muted-foreground">total events · last {days}d</span>
      </div>

      <div className="h-48 p-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No activity data for this period
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="activityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
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
                formatter={(value: number) => [formatNumber(value), "Events"]}
              />
              <Area
                type="monotone"
                dataKey="total_events"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="url(#activityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
