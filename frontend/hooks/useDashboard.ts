"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Category } from "@/lib/types";

/** Top repos by star count, optionally filtered by category. */
export function useTopRepos(category: Category, days: number) {
  return useQuery({
    queryKey: ["top-repos", category, days],
    queryFn: () =>
      api.getTopRepos(category === "all" ? undefined : category, days),
    staleTime: 60_000,
  });
}

/** Trending repos by star growth velocity (all categories). */
export function useTrending(days: number) {
  return useQuery({
    queryKey: ["trending", days],
    queryFn: () => api.getTrending(days),
    staleTime: 60_000,
  });
}

/** Star counts grouped by GitHub topic tag (top 30). */
export function useTopicBreakdown(days: number) {
  return useQuery({
    queryKey: ["topic-breakdown", days],
    queryFn: () => api.getTopicBreakdown(days),
    staleTime: 300_000,
  });
}

/** Star counts grouped by primary programming language. */
export function useLanguageBreakdown(days: number) {
  return useQuery({
    queryKey: ["language-breakdown", days],
    queryFn: () => api.getLanguageBreakdown(days),
    staleTime: 300_000,
  });
}

/** Per-category aggregate stats (repo count, stars, top repo, weekly delta). */
export function useCategorySummary() {
  return useQuery({
    queryKey: ["category-summary"],
    queryFn: api.getCategorySummary,
    staleTime: 300_000,
  });
}

/** Repos making the biggest weekly moves in absolute and percentage terms. */
export function useShockMovers(days: number) {
  return useQuery({
    queryKey: ["shock-movers", days],
    queryFn: () => api.getShockMovers(days),
    staleTime: 60_000,
  });
}

/** Topics gaining star activity versus the prior comparison window. */
export function useTopicRotation(days: number) {
  return useQuery({
    queryKey: ["topic-rotation", days],
    queryFn: () => api.getTopicRotation(days),
    staleTime: 120_000,
  });
}
