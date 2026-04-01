"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Neighbor recommendations for the selected repository. */
export function useAIRelatedRepos(
  repoName: string | null,
  days: number,
  limit = 6,
) {
  return useQuery({
    queryKey: ["ai-related-repos", repoName, days, limit],
    queryFn: () => api.getAIRelatedRepos(repoName!, days, limit),
    enabled: !!repoName,
    staleTime: 60_000,
  });
}
