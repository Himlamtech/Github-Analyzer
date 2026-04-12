"use client";

import { Treemap, ResponsiveContainer, Tooltip } from "recharts";

import { useTopicBreakdown } from "@/hooks/useDashboard";
import { formatNumber } from "@/lib/utils";

interface Props {
  days: number;
}

// Color scale: low (cool blue) → high (warm orange)
function getTopicColor(index: number, total: number): string {
  const ratio = 1 - index / Math.max(total - 1, 1);
  // Lerp between #1d4ed8 (blue-700) and #f97316 (orange-500)
  const r = Math.round(29 + (249 - 29) * ratio);
  const g = Math.round(78 + (115 - 78) * ratio);
  const b = Math.round(216 + (22 - 216) * ratio);
  return `rgb(${r},${g},${b})`;
}

interface TreemapContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  index?: number;
  root?: { children?: unknown[] };
}

function CustomContent({
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  name = "",
  index = 0,
  root,
}: TreemapContentProps) {
  const total = (root?.children as unknown[])?.length ?? 1;
  const color = getTopicColor(index, total);
  const showLabel = width > 40 && height > 24;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={width - 2}
        height={height - 2}
        style={{ fill: color, opacity: 0.85, strokeWidth: 0 }}
        rx={3}
      />
      {showLabel && (
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            fill: "#fff",
            fontSize: Math.min(12, width / 6),
            fontWeight: 500,
            pointerEvents: "none",
          }}
        >
          {name}
        </text>
      )}
    </g>
  );
}

export function TopicHeatmap({ days }: Props) {
  const { data, isLoading } = useTopicBreakdown(days);

  const treemapData = (data ?? []).map((d) => ({
    name: d.topic,
    size: d.event_count,
    repo_count: d.repo_count,
  }));

  return (
    <div className="card-glow overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Topic Heatmap</h2>
        <span className="text-xs text-muted-foreground">by stars · last {days}d</span>
      </div>

      <div className="h-72 p-3">
        {isLoading ? (
          <div className="grid h-full animate-pulse grid-cols-4 gap-1.5">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="rounded-md bg-muted" style={{ gridRow: i < 4 ? "span 2" : "span 1" }} />
            ))}
          </div>
        ) : treemapData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No topic data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={treemapData}
              dataKey="size"
              content={<CustomContent />}
            >
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: 12,
                }}
                formatter={(value: number, _name: string, props: { payload?: { name?: string; repo_count?: number } }) => [
                  `${formatNumber(value)} stars · ${props?.payload?.repo_count ?? 0} repos`,
                  props?.payload?.name ?? "",
                ]}
              />
            </Treemap>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
