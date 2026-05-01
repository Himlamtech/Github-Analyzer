"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

import { useLanguageBreakdown } from "@/hooks/useDashboard";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
}

// Top 8 language colors
const LANG_COLORS = [
  "#3b82f6", // blue
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#f59e0b", // amber
  "#10b981", // emerald
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#6b7280", // gray (for "Other")
];

export function LanguageDistChart({ days }: Props) {
  const { data, isLoading } = useLanguageBreakdown(days);

  const top8 = (data ?? []).slice(0, 8);
  const others = (data ?? []).slice(8);
  const otherSum = others.reduce((acc, d) => acc + d.event_count, 0);

  const chartData = [
    ...top8.map((d) => ({ name: d.language, value: d.event_count, repos: d.repo_count })),
    ...(otherSum > 0 ? [{ name: "Other", value: otherSum, repos: 0 }] : []),
  ];

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  return (
    <div className="card-glow overflow-hidden rounded-[28px] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-4">
        <div>
          <h2 className="text-sm font-semibold">Language Breakdown</h2>
          <p className="text-xs text-muted-foreground">Share of current repository activity by language</p>
        </div>
        <span className="text-xs text-muted-foreground">by stars · last {days}d</span>
      </div>

      <div className="h-80 p-3">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No language data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="40%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={LANG_COLORS[index % LANG_COLORS.length]}
                    opacity={0.9}
                  />
                ))}
              </Pie>

              {/* Center label */}
              <text
                x="40%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="central"
                style={{ fill: "hsl(var(--foreground))", fontSize: 11, fontWeight: 600 }}
              >
                {formatNumber(total)}
              </text>
              <text
                x="40%"
                y="50%"
                dy={14}
                textAnchor="middle"
                style={{ fill: "hsl(var(--muted-foreground))", fontSize: 9 }}
              >
                total stars
              </text>

              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [
                  `${formatNumber(value)} (${Math.round((value / total) * 100)}%)`,
                  name,
                ]}
              />
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, color: "hsl(var(--muted-foreground))" }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
