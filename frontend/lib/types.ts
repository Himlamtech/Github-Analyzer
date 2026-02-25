// TypeScript interfaces — mirrors backend DTOs in src/application/dtos/repo_metadata_dto.py
// Keep in sync with backend when adding new fields.

export type Category =
  | "LLM"
  | "Agent"
  | "Diffusion"
  | "Multimodal"
  | "DataEng"
  | "Other"
  | "all";

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
  event_count: number;
  repo_count: number;
}

export interface LanguageBreakdown {
  language: string;
  event_count: number;
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
