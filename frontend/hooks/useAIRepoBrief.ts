"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RepoBriefResponse } from "@/lib/types";

/** Grounded AI repo brief for a selected repository. */
export function useAIRepoBrief(repoName: string | null, days: number) {
  return useQuery<RepoBriefResponse>({
    queryKey: ["ai-repo-brief", repoName, days],
    queryFn: () => api.getRepoBrief(repoName!, days),
    enabled: !!repoName,
    staleTime: 120_000,
  });
}
