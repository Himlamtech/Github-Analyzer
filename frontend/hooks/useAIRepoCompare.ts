"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RepoCompareResponse } from "@/lib/types";

/** Grounded AI comparison between two repositories. */
export function useAIRepoCompare(
  baseRepoName: string | null,
  compareRepoName: string | null,
  days: number,
) {
  return useQuery<RepoCompareResponse>({
    queryKey: ["ai-repo-compare", baseRepoName, compareRepoName, days],
    queryFn: () => api.getRepoCompare(baseRepoName!, compareRepoName!, days),
    enabled: !!baseRepoName && !!compareRepoName,
    staleTime: 120_000,
  });
}
