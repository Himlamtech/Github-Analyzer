"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RelatedReposResponse } from "@/lib/types";

/** Related repository recommendations for a selected repo. */
export function useAIRelatedRepos(
  repoName: string | null,
  days: number,
  limit = 6,
) {
  return useQuery<RelatedReposResponse>({
    queryKey: ["ai-related-repos", repoName, days, limit],
    queryFn: () => api.getRelatedRepos(repoName!, days, limit),
    enabled: !!repoName,
    staleTime: 120_000,
  });
}
