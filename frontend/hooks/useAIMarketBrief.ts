"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** On-demand market brief summarizing current breakout activity. */
export function useAIMarketBrief(days: number, enabled: boolean) {
  return useQuery({
    queryKey: ["ai-market-brief", days],
    queryFn: () => api.getAIMarketBrief(days),
    enabled,
    staleTime: 60_000,
  });
}
