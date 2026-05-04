"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Category } from "@/lib/types";

/** Top repos by star count, optionally filtered by category. */
export function useTopRepos(category: Category, days: number, limit = 20) {
  return useQuery({
    queryKey: ["top-repos", category, days, limit],
    queryFn: () =>
      api.getTopRepos(category === "all" ? undefined : category, days, limit),
    staleTime: 60_000,
  });
}

/** Top repos by all-time current total stars, optionally filtered by category. */
export function useTopStarredRepos(category: Category, limit = 20) {
  return useQuery({
    queryKey: ["top-starred-repos", category, limit],
    queryFn: () =>
      api.getTopStarredRepos(category === "all" ? undefined : category, limit),
    staleTime: 60_000,
  });
}

/** Repos gaining the most stars since Monday 00:00 GMT+7. */
export function useTrending(days: number, limit = 10) {
  return useQuery({
    queryKey: ["trending", days, limit],
    queryFn: () => api.getTrending(days, limit),
    staleTime: 60_000,
  });
}

/** Strongest absolute and percentage-based movers in the selected window. */
export function useShockMovers(days: number) {
  return useQuery({
    queryKey: ["shock-movers", days],
    queryFn: () => api.getShockMovers(days),
    staleTime: 60_000,
  });
}

/** Topics accelerating fastest compared with the prior matching window. */
export function useTopicRotation(days: number) {
  return useQuery({
    queryKey: ["topic-rotation", days],
    queryFn: () => api.getTopicRotation(days),
    staleTime: 60_000,
  });
}

/** External headline bundle for the current breakout repositories. */
export function useNewsRadar(days: number) {
  return useQuery({
    queryKey: ["news-radar", days],
    queryFn: () => api.getNewsRadar(days),
    staleTime: 120_000,
    retry: false,
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
