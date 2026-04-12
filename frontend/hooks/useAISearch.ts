"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { AISearchResponse, Category } from "@/lib/types";

interface UseAISearchParams {
  query: string;
  category?: Category;
  days: number;
  language?: string;
  minStars: number;
  limit?: number;
  enabled?: boolean;
}

/** Natural-language repository search with explainable AI ranking. */
export function useAISearch({
  query,
  category,
  days,
  language,
  minStars,
  limit = 8,
  enabled = true,
}: UseAISearchParams) {
  return useQuery<AISearchResponse>({
    queryKey: ["ai-search", query, category, days, language, minStars, limit],
    queryFn: () =>
      api.getAISearch({
        query,
        category: category === "all" ? undefined : category,
        days,
        language,
        minStars,
        limit,
      }),
    enabled: enabled && query.trim().length >= 2,
    staleTime: 60_000,
  });
}
