"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

interface UseAISearchParams {
  query: string;
  category?: string;
  days: number;
  language?: string;
  minStars: number;
  limit?: number;
  enabled?: boolean;
}

/** Natural-language repository discovery with lexical or hybrid retrieval. */
export function useAISearch({
  query,
  category,
  days,
  language,
  minStars,
  limit = 12,
  enabled = true,
}: UseAISearchParams) {
  return useQuery({
    queryKey: ["ai-search", query, category, days, language, minStars, limit],
    queryFn: () =>
      api.searchRepositories({
        query,
        category,
        days,
        language,
        limit,
        minStars,
      }),
    enabled: enabled && query.trim().length >= 2,
    staleTime: 30_000,
  });
}
