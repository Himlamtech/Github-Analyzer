"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { MarketBriefResponse } from "@/lib/types";

/** Grounded AI market brief for the active dashboard window. */
export function useAIMarketBrief(days: number, enabled = false) {
  return useQuery<MarketBriefResponse>({
    queryKey: ["ai-market-brief", days],
    queryFn: () => api.getMarketBrief(days),
    enabled,
    staleTime: 120_000,
  });
}
