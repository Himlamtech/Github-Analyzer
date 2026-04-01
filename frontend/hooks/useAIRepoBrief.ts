"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

/** Grounded repository brief for a selected repo. */
export function useAIRepoBrief(repoName: string | null, days: number) {
  return useQuery({
    queryKey: ["ai-repo-brief", repoName, days],
    queryFn: () => api.getAIRepoBrief(repoName!, days),
    enabled: !!repoName,
    staleTime: 60_000,
  });
}
