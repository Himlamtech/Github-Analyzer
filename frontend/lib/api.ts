// Typed API client for the GitHub AI Trend Analyzer backend.
// All functions throw on non-2xx HTTP responses.

import type {
  CategorySummary,
  LanguageBreakdown,
  TimeseriesPoint,
  TopicBreakdown,
  TopRepo,
  TrendingRepo,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) =>
      url.searchParams.set(k, String(v)),
    );
  }
  const res = await fetch(url.toString(), {
    next: { revalidate: 60 },
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getTopRepos: (
    category?: string,
    days = 7,
    limit = 20,
  ): Promise<TopRepo[]> =>
    apiFetch<TopRepo[]>("/dashboard/top-repos", {
      ...(category && category !== "all" ? { category } : {}),
      days,
      limit,
    }),

  getTrending: (days = 7, limit = 20): Promise<TrendingRepo[]> =>
    apiFetch<TrendingRepo[]>("/dashboard/trending", { days, limit }),

  getTopicBreakdown: (days = 7): Promise<TopicBreakdown[]> =>
    apiFetch<TopicBreakdown[]>("/dashboard/topic-breakdown", { days }),

  getLanguageBreakdown: (days = 7): Promise<LanguageBreakdown[]> =>
    apiFetch<LanguageBreakdown[]>("/dashboard/language-breakdown", { days }),

  getRepoTimeseries: (
    repo_name: string,
    days = 30,
  ): Promise<TimeseriesPoint[]> =>
    apiFetch<TimeseriesPoint[]>("/dashboard/repo-timeseries", {
      repo_name,
      days,
    }),

  getCategorySummary: (): Promise<CategorySummary[]> =>
    apiFetch<CategorySummary[]>("/dashboard/category-summary"),
};
