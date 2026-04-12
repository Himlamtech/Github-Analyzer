// Typed API client for the GitHub AI Trend Analyzer backend.
// All functions throw on non-2xx HTTP responses.

import type {
  AISearchResponse,
  CategorySummary,
  LanguageBreakdown,
  MarketBriefResponse,
  NewsRadarResponse,
  RelatedReposResponse,
  RepoCompareResponse,
  RepoBriefResponse,
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
    // SSR inside Docker: use the internal service hostname
    const base = process.env.API_INTERNAL_URL ?? "http://api:8000";
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

export const api = {
  getMarketBrief: (
    days = 30,
    breakoutLimit = 5,
    categoryLimit = 4,
    topicLimit = 6,
  ): Promise<MarketBriefResponse> =>
    apiFetch<MarketBriefResponse>("/ai/market-brief", {
      days,
      breakout_limit: breakoutLimit,
      category_limit: categoryLimit,
      topic_limit: topicLimit,
    }),

  getRelatedRepos: (
    repoName: string,
    days = 30,
    limit = 6,
  ): Promise<RelatedReposResponse> =>
    apiFetch<RelatedReposResponse>("/ai/related-repos", {
      repo_name: repoName,
      days,
      limit,
    }),

  getRepoCompare: (
    baseRepoName: string,
    compareRepoName: string,
    days = 30,
  ): Promise<RepoCompareResponse> =>
    apiFetch<RepoCompareResponse>("/ai/repo-compare", {
      base_repo_name: baseRepoName,
      compare_repo_name: compareRepoName,
      days,
    }),

  getRepoBrief: (repoName: string, days = 30): Promise<RepoBriefResponse> =>
    apiFetch<RepoBriefResponse>("/ai/repo-brief", {
      repo_name: repoName,
      days,
    }),

  getAISearch: ({
    query,
    category,
    days = 30,
    language,
    minStars = 10_000,
    limit = 8,
  }: {
    query: string;
    category?: string;
    days?: number;
    language?: string;
    minStars?: number;
    limit?: number;
  }): Promise<AISearchResponse> =>
    apiFetch<AISearchResponse>("/ai/search", {
      query,
      ...(category ? { category } : {}),
      ...(language ? { language } : {}),
      days,
      min_stars: minStars,
      limit,
    }),

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

  getNewsRadar: (
    days = 7,
    repoLimit = 4,
    focus: "absolute" | "percentage" = "percentage",
    minBaselineStars = 1_000,
  ): Promise<NewsRadarResponse> =>
    apiFetch<NewsRadarResponse>("/dashboard/news-radar", {
      days,
      repo_limit: repoLimit,
      focus,
      min_baseline_stars: minBaselineStars,
    }),

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
