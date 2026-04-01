// TypeScript interfaces — mirrors backend DTOs in src/application/dtos/repo_metadata_dto.py
// Keep in sync with backend when adding new fields.

export type Category = string;

export interface RepoMetadata {
  repo_id: number;
  repo_full_name: string;
  repo_name: string;
  html_url: string;
  description: string;
  primary_language: string;
  topics: string[];
  category: string;
  stargazers_count: number;
  watchers_count: number;
  forks_count: number;
  open_issues_count: number;
  subscribers_count: number;
  owner_login: string;
  owner_avatar_url: string;
  license_name: string;
  github_created_at: string;
  github_pushed_at: string;
  rank: number;
}

export interface TopRepo {
  repo: RepoMetadata;
  star_count_in_window: number;
  star_delta: number;
}

export interface TrendingRepo {
  repo: RepoMetadata;
  star_count_in_window: number;
  growth_rank: number;
}

export interface TopicBreakdown {
  topic: string;
  star_count: number;
  repo_count: number;
}

export interface LanguageBreakdown {
  language: string;
  star_count: number;
  repo_count: number;
}

export interface TimeseriesPoint {
  event_date: string;
  star_count: number;
  total_events: number;
}

export interface CategorySummary {
  category: string;
  repo_count: number;
  total_stars: number;
  top_repo_name: string;
  top_repo_stars: number;
  weekly_star_delta: number;
}

export interface TopicRotationItem {
  topic: string;
  current_star_count: number;
  previous_star_count: number;
  star_delta: number;
  repo_count: number;
  rank: number;
}

export interface ShockMover {
  repo: RepoMetadata;
  star_count_in_window: number;
  previous_star_count_in_window: number;
  unique_actors_in_window: number;
  weekly_percent_gain: number;
  window_over_window_ratio: number;
  rank: number;
}

export interface ShockMoversResponse {
  window_days: number;
  absolute_movers: ShockMover[];
  percentage_movers: ShockMover[];
}

export interface RepoSearchFilters {
  category: string | null;
  primary_language: string | null;
  min_stars: number;
  days: number;
}

export interface RepoSearchResult {
  repo: RepoMetadata;
  star_count_in_window: number;
  score: number;
  lexical_score: number;
  semantic_score: number | null;
  popularity_score: number;
  matched_terms: string[];
  why_matched: string[];
}

export interface RepoSearchResponse {
  query: string;
  normalized_query: string;
  retrieval_mode: "lexical" | "hybrid";
  total_candidates: number;
  returned_results: number;
  filters: RepoSearchFilters;
  results: RepoSearchResult[];
}

export interface RepoBriefActivity {
  event_type: string;
  event_count: number;
}

export interface RepoBriefResponse {
  repo: RepoMetadata;
  window_days: number;
  retrieval_mode: "template" | "model";
  trend_verdict: "accelerating" | "steady" | "emerging" | "quiet";
  headline: string;
  summary: string;
  why_trending: string;
  star_count_in_window: number;
  total_events_in_window: number;
  unique_actors_in_window: number;
  latest_event_at: string | null;
  activity_breakdown: RepoBriefActivity[];
  key_signals: string[];
  watchouts: string[];
}

export interface RepoCompareMetric {
  key: string;
  label: string;
  base_value: number;
  compare_value: number;
  winner: "base" | "compare" | "tie";
}

export interface RepoCompareResponse {
  base_repo: RepoMetadata;
  compare_repo: RepoMetadata;
  window_days: number;
  retrieval_mode: "template" | "model";
  overall_winner: "base" | "compare" | "tie";
  headline: string;
  summary: string;
  key_differences: string[];
  when_to_choose_base: string[];
  when_to_choose_compare: string[];
  metric_snapshot: RepoCompareMetric[];
}

export interface RelatedRepoResult {
  repo: RepoMetadata;
  similarity_score: number;
  star_count_in_window: number;
  shared_topics: string[];
  why_related: string[];
}

export interface RelatedReposResponse {
  source_repo: RepoMetadata;
  total_candidates: number;
  returned_results: number;
  results: RelatedRepoResult[];
}

export interface MarketBreakoutRepo {
  repo: RepoMetadata;
  star_count_in_window: number;
  total_events_in_window: number;
  unique_actors_in_window: number;
  momentum_score: number;
}

export interface MarketCategoryMover {
  category: string;
  active_repo_count: number;
  total_stars_in_window: number;
  total_events_in_window: number;
  leader_repo_name: string;
  leader_stars_in_window: number;
  share_of_window_stars: number;
}

export interface MarketTopicShift {
  topic: string;
  repo_count: number;
  star_count_in_window: number;
}

export interface MarketBriefResponse {
  window_days: number;
  generated_at: string;
  retrieval_mode: "template" | "model";
  headline: string;
  summary: string;
  key_takeaways: string[];
  watchouts: string[];
  breakout_repos: MarketBreakoutRepo[];
  category_movers: MarketCategoryMover[];
  topic_shifts: MarketTopicShift[];
}

export const CATEGORY_COLORS: Record<string, string> = {
  LLM: "#3b82f6",       // blue-500
  Agent: "#8b5cf6",     // violet-500
  Diffusion: "#ec4899", // pink-500
  Multimodal: "#f59e0b",// amber-500
  DataEng: "#10b981",   // emerald-500
  Other: "#6b7280",     // gray-500
};

export const CATEGORY_LABELS: Record<string, string> = {
  LLM: "Large Language Models",
  Agent: "AI Agents & RAG",
  Diffusion: "Image Generation",
  Multimodal: "Multimodal AI",
  DataEng: "Data & Embeddings",
  Other: "Other AI/ML",
};
