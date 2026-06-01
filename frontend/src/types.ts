export interface Repository {
  id: string;
  name: string;
  owner: string;
  fullName: string;
  description: string;
  sector: string;
  starCount: number;
  velocityIndex: number;
  velocityChange: string;
  durableMomentum: number;
  hypeRisk: 'Low' | 'Moderate' | 'Elevated' | 'Extreme';
  sparkline: number[];
  activeContributors: number;
  commits24h: number;
  language: string;
  topics: string[];
  rank: number;
  lastPushedAt: string;
  repoUrl: string;
  breakoutScore: number;
  confidenceScore: number;
  hypeRiskScore: number;
  starGain7d: number;
  starGainVsPreviousWindow: number;
  explanationTrace: string[];
}

export interface EcosystemCategory {
  id: string;
  title: string;
  score: number;
  growth: string;
  momentum: number;
  description: string;
  topRepos?: string[];
  topTopics?: string[];
  confidenceScore?: number;
  rotationDrivers?: string[];
}

export interface NewsImpactEvent {
  id: string;
  date: string;
  timeOffset: string;
  headline: string;
  category: string;
  summary: string;
  causalityScore: number;
  codeImpactMetric: string;
  narrativeText: string;
  linkedEntities: string[];
  topImpactedRepos: string[];
  codeTrendData: { time: string; value: number }[];
}

export interface WeeklyBriefPillar {
  pillarNumber: string;
  title: string;
  description: string;
}

export interface FrameworkRadarItem {
  id: string;
  name: string;
  developerVelocity: number;
  commercialReadiness: number;
  contributorEnergy: number;
  marketFootprint: string;
  strategicInsight: string;
}

export interface RadarSummaryItem {
  title: string;
  summary: string;
}

export interface FrameworkRadarSnapshot {
  generatedAt: string;
  frameworks: FrameworkRadarItem[];
  winners: RadarSummaryItem[];
  warnings: RadarSummaryItem[];
}

export interface WeeklyBriefRegion {
  region: string;
  status: string;
  activePercentage: number;
}

export interface WeeklyBriefAuthor {
  initials: string;
  name: string;
  role: string;
}

export interface WeeklyBriefChartPoint {
  period: string;
  standardRAG: number;
  agenticLoops: number;
}

export interface WeeklyBriefSnapshot {
  briefId: string;
  publishedAt: string;
  title: string;
  subtitle: string;
  pillars: WeeklyBriefPillar[];
  summaryChartData: WeeklyBriefChartPoint[];
  evidenceSpotlightTitle: string;
  evidenceSpotlightBody: string;
  evidenceSpotlightBadge: string;
  regionalIndicators: WeeklyBriefRegion[];
  authors: WeeklyBriefAuthor[];
  disclaimer: string;
}

export interface PipelineStatus {
  clickhouseReachable: boolean;
  parquetPathExists: boolean;
  dataFreshnessSeconds: number | null;
  status: string;
}

export interface EventSummary {
  eventId: string;
  eventType: string;
  actorLogin: string;
  repoName: string;
  createdAt: string;
}

export interface DashboardSnapshot {
  topRepos: Repository[];
  trendingRepos: Repository[];
  topicRotation: EcosystemCategory[];
  latestEvents: EventSummary[];
  pipelineStatus: PipelineStatus | null;
  refreshedAt: string;
}

export interface RepoTimeseriesPoint {
  eventDate: string;
  starCount: number;
  totalEvents: number;
}

export interface DashboardApiRepo {
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

export interface TopRepoResponse {
  repo: DashboardApiRepo;
  star_count_in_window: number;
  star_delta: number;
}

export interface TrendingRepoResponse {
  repo: DashboardApiRepo;
  star_count_in_window: number;
  growth_rank: number;
}

export interface TopicRotationResponse {
  topic: string;
  current_star_count: number;
  previous_star_count: number;
  star_delta: number;
  repo_count: number;
  rank: number;
}

export interface RotationCategoryResponse {
  category: string;
  current_attention_score: number;
  previous_attention_score: number;
  attention_delta: number;
  repo_count: number;
  top_repos: string[];
  top_topics: string[];
  confidence_score: number;
  rotation_drivers: string[];
  last_computed_at: string;
}

export interface PipelineStatusResponse {
  clickhouse_reachable: boolean;
  parquet_path_exists: boolean;
  data_freshness_seconds: number | null;
  status: string;
}

export interface EventSummaryResponse {
  event_id: string;
  event_type: string;
  actor_login: string;
  repo_name: string;
  created_at: string;
}

export interface RepoTimeseriesResponse {
  event_date: string;
  star_count: number;
  total_events: number;
}

export interface BreakoutRepositoryResponse {
  repo: DashboardApiRepo;
  breakout_score: number;
  durability_score: number;
  hype_risk_score: number;
  confidence_score: number;
  star_gain_7d: number;
  unique_actors_7d: number;
  event_count_7d: number;
  star_gain_vs_previous_window: number;
  explanation_trace: string[];
  last_computed_at: string;
}

export interface NewsImpactCurvePointResponse {
  time_bucket: string;
  value: number;
}

export interface NewsImpactEventResponse {
  event_id: string;
  source: string;
  headline: string;
  published_at: string;
  provider: string;
  event_type: string;
  linked_entities: string[];
  linked_categories: string[];
  causality_score: number;
  lag_hours: number;
  impact_summary: string;
  impact_curve: NewsImpactCurvePointResponse[];
  top_impacted_repos: string[];
  explanation_trace: string[];
  last_computed_at: string;
}

export interface RadarSummaryResponse {
  title: string;
  summary: string;
}

export interface FrameworkRadarItemResponse {
  framework_id: string;
  framework_name: string;
  velocity_score: number;
  commercial_readiness_score: number;
  contributor_energy_score: number;
  market_footprint: string;
  strategic_insight_summary: string;
}

export interface FrameworkRadarSnapshotResponse {
  generated_at: string;
  frameworks: FrameworkRadarItemResponse[];
  winners: RadarSummaryResponse[];
  warnings: RadarSummaryResponse[];
}

export interface WeeklyBriefPillarResponse {
  pillar_number: string;
  title: string;
  description: string;
}

export interface WeeklyBriefChartPointResponse {
  period: string;
  standard_rag: number;
  agentic_loops: number;
}

export interface WeeklyBriefRegionResponse {
  region: string;
  status: string;
  active_percentage: number;
}

export interface WeeklyBriefAuthorResponse {
  initials: string;
  name: string;
  role: string;
}

export interface WeeklyBriefSnapshotResponse {
  brief_id: string;
  published_at: string;
  title: string;
  subtitle: string;
  pillars: WeeklyBriefPillarResponse[];
  summary_chart_data: WeeklyBriefChartPointResponse[];
  evidence_spotlight_title: string;
  evidence_spotlight_body: string;
  evidence_spotlight_badge: string;
  regional_indicators: WeeklyBriefRegionResponse[];
  authors: WeeklyBriefAuthorResponse[];
  disclaimer: string;
}
