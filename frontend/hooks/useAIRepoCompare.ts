"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Grounded comparison between two repositories. */
export function useAIRepoCompare(
  baseRepoName: string | null,
  compareRepoName: string | null,
  days: number,
) {
  return useQuery({
    queryKey: ["ai-repo-compare", baseRepoName, compareRepoName, days],
    queryFn: () => api.getAIRepoCompare(baseRepoName!, compareRepoName!, days),
    enabled: !!baseRepoName && !!compareRepoName,
    staleTime: 60_000,
  });
}
