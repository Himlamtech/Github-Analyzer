// Typed API client for the GitHub AI Trend Analyzer backend.
// All functions throw on non-2xx HTTP responses.

import type {
  CategorySummary,
  LanguageBreakdown,
  ShockMoversResponse,
  TimeseriesPoint,
  TopicRotation,
  TopicBreakdown,
  TopRepo,
  TrendingRepo,
} from "./types";

// For SSR (server-side): call the API container directly.
// For browser (client-side): use relative URLs — Next.js rewrites proxy them
// to the API container, so the browser never needs to resolve 'api:8000'.
function buildUrl(path: string): URL {
  if (typeof window === "undefined") {
    // SSR inside Docker uses API_INTERNAL_URL; local development falls back to localhost.
    const base = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
    return new URL(`${base}${path}`);
  }
  // Browser: relative path, proxied by Next.js rewrites
  return new URL(path, window.location.origin);
}

async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<T> {
  const url = buildUrl(path);
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

async function apiPost<T>(path: string, body: object): Promise<T> {
  const url = buildUrl(path);
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
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

  getTopStarredRepos: (
    category?: string,
    limit = 20,
  ): Promise<TopRepo[]> =>
    apiFetch<TopRepo[]>("/dashboard/top-starred-repos", {
      ...(category && category !== "all" ? { category } : {}),
      limit,
    }),

  getTrending: (days = 7, limit = 10): Promise<TrendingRepo[]> =>
    apiFetch<TrendingRepo[]>("/dashboard/trending", { days, limit }),

  getShockMovers: (
    days = 7,
    absoluteLimit = 6,
    percentageLimit = 6,
    minBaselineStars = 1_000,
  ): Promise<ShockMoversResponse> =>
    apiFetch<ShockMoversResponse>("/dashboard/shock-movers", {
      days,
      absolute_limit: absoluteLimit,
      percentage_limit: percentageLimit,
      min_baseline_stars: minBaselineStars,
    }),

  getTopicRotation: (days = 7, limit = 8): Promise<TopicRotation[]> =>
    apiFetch<TopicRotation[]>("/dashboard/topic-rotation", { days, limit }),

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
