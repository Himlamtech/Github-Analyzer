"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Daily star count + total event count for a specific repository. */
export function useRepoTimeseries(repoName: string | null, days: number) {
  return useQuery({
    queryKey: ["repo-timeseries", repoName, days],
    queryFn: () => api.getRepoTimeseries(repoName!, days),
    enabled: !!repoName,
    staleTime: 120_000,
  });
}
