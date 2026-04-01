// Typed API client for the GitHub AI Trend Analyzer backend.
// All functions throw on non-2xx HTTP responses.

import type {
  CategorySummary,
  LanguageBreakdown,
  MarketBriefResponse,
  RelatedReposResponse,
  RepoBriefResponse,
  RepoCompareResponse,
  RepoSearchResponse,
  ShockMoversResponse,
  TimeseriesPoint,
  TopicBreakdown,
  TopicRotationItem,
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

  getShockMovers: (
    days = 7,
    absolute_limit = 10,
    percentage_limit = 10,
    min_baseline_stars = 500,
  ): Promise<ShockMoversResponse> =>
    apiFetch<ShockMoversResponse>("/dashboard/shock-movers", {
      days,
      absolute_limit,
      percentage_limit,
      min_baseline_stars,
    }),

  getTopicRotation: (days = 7, limit = 12): Promise<TopicRotationItem[]> =>
    apiFetch<TopicRotationItem[]>("/dashboard/topic-rotation", {
      days,
      limit,
    }),

  searchRepositories: ({
    query,
    category,
    days = 7,
    language,
    limit = 12,
    minStars = 10_000,
  }: {
    query: string;
    category?: string;
    days?: number;
    language?: string;
    limit?: number;
    minStars?: number;
  }): Promise<RepoSearchResponse> =>
    apiFetch<RepoSearchResponse>("/ai/search", {
      query,
      ...(category ? { category } : {}),
      ...(language ? { language } : {}),
      days,
      limit,
      min_stars: minStars,
    }),

  getAIMarketBrief: (
    days = 7,
    breakout_limit = 3,
    category_limit = 2,
    topic_limit = 3,
  ): Promise<MarketBriefResponse> =>
    apiFetch<MarketBriefResponse>("/ai/market-brief", {
      days,
      breakout_limit,
      category_limit,
      topic_limit,
    }),

  getAIRepoBrief: (repo_name: string, days = 7): Promise<RepoBriefResponse> =>
    apiFetch<RepoBriefResponse>("/ai/repo-brief", {
      repo_name,
      days,
    }),

  getAIRepoCompare: (
    base_repo_name: string,
    compare_repo_name: string,
    days = 7,
  ): Promise<RepoCompareResponse> =>
    apiFetch<RepoCompareResponse>("/ai/repo-compare", {
      base_repo_name,
      compare_repo_name,
      days,
    }),

  getAIRelatedRepos: (
    repo_name: string,
    days = 7,
    limit = 6,
  ): Promise<RelatedReposResponse> =>
    apiFetch<RelatedReposResponse>("/ai/related-repos", {
      repo_name,
      days,
      limit,
    }),
};
