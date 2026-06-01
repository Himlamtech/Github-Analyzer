import type {
  BreakoutRepositoryResponse,
  DashboardApiRepo,
  DashboardSnapshot,
  EcosystemCategory,
  EventSummary,
  EventSummaryResponse,
  FrameworkRadarItem,
  FrameworkRadarItemResponse,
  FrameworkRadarSnapshot,
  FrameworkRadarSnapshotResponse,
  NewsImpactEvent,
  NewsImpactEventResponse,
  PipelineStatus,
  PipelineStatusResponse,
  RepoTimeseriesPoint,
  RepoTimeseriesResponse,
  Repository,
  RotationCategoryResponse,
  TopRepoResponse,
  TrendingRepoResponse,
  WeeklyBriefChartPoint,
  WeeklyBriefChartPointResponse,
  WeeklyBriefSnapshot,
  WeeklyBriefSnapshotResponse,
} from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')
  ?? 'http://localhost:8000';

const DEFAULT_REPOSITORY_SPARKLINE = [18, 24, 30, 38, 49, 60, 74, 88];

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  Other: 'General-purpose repositories currently driving measurable GitHub attention.',
};

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

async function requestJson<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function toTitleCase(value: string): string {
  if (!value) {
    return 'Other';
  }

  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function formatPercent(value: number): string {
  const rounded = Math.round(value);
  return `${rounded >= 0 ? '+' : ''}${rounded}%`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function inferHypeRisk(starDelta: number): Repository['hypeRisk'] {
  if (starDelta >= 250) {
    return 'Extreme';
  }
  if (starDelta >= 100) {
    return 'Elevated';
  }
  if (starDelta >= 30) {
    return 'Moderate';
  }
  return 'Low';
}

function normalizeSparkline(seed: number): number[] {
  if (seed <= 0) {
    return DEFAULT_REPOSITORY_SPARKLINE;
  }

  return [0.28, 0.34, 0.4, 0.52, 0.63, 0.74, 0.87, 1].map((multiplier) =>
    Math.max(4, Math.round(seed * multiplier)),
  );
}

function toRepository(
  repo: DashboardApiRepo,
  rank: number,
  starCountInWindow: number,
  velocityRank: number,
): Repository {
  const velocityIndex = clamp(Number((starCountInWindow / 12 + 4.5).toFixed(1)), 4.5, 9.9);
  const durableMomentum = clamp(
    Math.round((repo.watchers_count + repo.forks_count + starCountInWindow) / Math.max(repo.stargazers_count, 1) * 1000),
    18,
    96,
  );
  const activeContributors = Math.max(8, Math.round(starCountInWindow / 2));
  const commits24h = Math.max(3, Math.round(starCountInWindow / 3));

  return {
    id: String(repo.repo_id),
    name: repo.repo_name,
    owner: repo.owner_login,
    fullName: repo.repo_full_name,
    description: repo.description || 'No repository description available.',
    sector: toTitleCase(repo.category),
    starCount: repo.stargazers_count,
    velocityIndex,
    velocityChange: formatPercent(starCountInWindow),
    durableMomentum,
    hypeRisk: inferHypeRisk(starCountInWindow),
    sparkline: normalizeSparkline(starCountInWindow),
    activeContributors,
    commits24h,
    language: repo.primary_language || 'Unknown',
    topics: repo.topics,
    rank: velocityRank || rank,
    lastPushedAt: repo.github_pushed_at,
    repoUrl: repo.html_url,
    breakoutScore: velocityIndex * 10,
    confidenceScore: durableMomentum,
    hypeRiskScore: starCountInWindow,
    starGain7d: starCountInWindow,
    starGainVsPreviousWindow: starCountInWindow,
    explanationTrace: ['Derived from dashboard analytics snapshot.'],
  };
}

function toBreakoutRepository(item: BreakoutRepositoryResponse, index: number): Repository {
  const base = toRepository(item.repo, index + 1, item.star_gain_7d, index + 1);

  return {
    ...base,
    durableMomentum: Math.round(item.durability_score),
    hypeRisk: inferHypeRisk(item.hype_risk_score),
    activeContributors: item.unique_actors_7d,
    commits24h: Math.max(3, Math.round(item.event_count_7d / 3)),
    breakoutScore: item.breakout_score,
    confidenceScore: item.confidence_score,
    hypeRiskScore: item.hype_risk_score,
    starGain7d: item.star_gain_7d,
    starGainVsPreviousWindow: item.star_gain_vs_previous_window,
    explanationTrace: item.explanation_trace,
  };
}

function toPipelineStatus(response: PipelineStatusResponse): PipelineStatus {
  return {
    clickhouseReachable: response.clickhouse_reachable,
    parquetPathExists: response.parquet_path_exists,
    dataFreshnessSeconds: response.data_freshness_seconds,
    status: response.status,
  };
}

function toEventSummary(response: EventSummaryResponse): EventSummary {
  return {
    eventId: response.event_id,
    eventType: response.event_type,
    actorLogin: response.actor_login,
    repoName: response.repo_name,
    createdAt: response.created_at,
  };
}

function toEcosystemCategory(row: RotationCategoryResponse): EcosystemCategory {
  const score = clamp(Number((row.attention_delta / 20 + 5).toFixed(1)), 1, 10);
  const momentum = clamp(
    Math.round((row.current_attention_score / Math.max(row.previous_attention_score || 1, 1)) * 40),
    12,
    98,
  );

  return {
    id: `rotation-${row.category.toLowerCase().replace(/\s+/g, '-')}`,
    title: row.category,
    score,
    growth: formatPercent(row.attention_delta),
    momentum,
    description:
      CATEGORY_DESCRIPTIONS[row.category]
      ?? `${row.repo_count} repositories contributed to this category rotation in the current window.`,
    topRepos: row.top_repos,
    topTopics: row.top_topics,
    confidenceScore: row.confidence_score,
    rotationDrivers: row.rotation_drivers,
  };
}

function toNewsImpactEvent(row: NewsImpactEventResponse): NewsImpactEvent {
  return {
    id: row.event_id,
    date: new Date(row.published_at).toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      timeZone: 'UTC',
    }),
    timeOffset: `${row.lag_hours} Hours After`,
    headline: row.headline,
    category: row.linked_categories[0] ?? row.event_type,
    summary: row.explanation_trace[0] ?? row.impact_summary,
    causalityScore: Math.round(row.causality_score),
    codeImpactMetric: row.impact_summary,
    narrativeText: row.explanation_trace.join(' '),
    linkedEntities: row.linked_entities,
    topImpactedRepos: row.top_impacted_repos,
    codeTrendData: row.impact_curve.map((point) => ({
      time: point.time_bucket,
      value: point.value,
    })),
  };
}

function toFrameworkRadarItem(row: FrameworkRadarItemResponse): FrameworkRadarItem {
  return {
    id: row.framework_id,
    name: row.framework_name,
    developerVelocity: row.velocity_score,
    commercialReadiness: row.commercial_readiness_score,
    contributorEnergy: row.contributor_energy_score,
    marketFootprint: row.market_footprint,
    strategicInsight: row.strategic_insight_summary,
  };
}

function toWeeklyBriefChartPoint(row: WeeklyBriefChartPointResponse): WeeklyBriefChartPoint {
  return {
    period: row.period,
    standardRAG: row.standard_rag,
    agenticLoops: row.agentic_loops,
  };
}

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const [topRepos, trendingRepos, topicRotation, latestEvents, pipelineStatus] = await Promise.all([
    requestJson<TopRepoResponse[]>('/dashboard/top-repos', { days: 7, limit: 12 }),
    requestJson<TrendingRepoResponse[]>('/dashboard/trending', { days: 7, limit: 6 }),
    requestJson<RotationCategoryResponse[]>('/intelligence/rotation', { days: 7, limit: 6 }),
    requestJson<EventSummaryResponse[]>('/events/latest', { limit: 6 }),
    requestJson<PipelineStatusResponse>('/pipeline/status'),
  ]);

  return {
    topRepos: topRepos.map((item, index) => toRepository(item.repo, index + 1, item.star_count_in_window, index + 1)),
    trendingRepos: trendingRepos.map((item, index) =>
      toRepository(item.repo, index + 1, item.star_count_in_window, item.growth_rank),
    ),
    topicRotation: topicRotation.map(toEcosystemCategory),
    latestEvents: latestEvents.map(toEventSummary),
    pipelineStatus: toPipelineStatus(pipelineStatus),
    refreshedAt: new Date().toISOString(),
  };
}

export async function fetchRepoTimeseries(repoName: string, days = 30): Promise<RepoTimeseriesPoint[]> {
  const rows = await requestJson<RepoTimeseriesResponse[]>('/dashboard/repo-timeseries', {
    repo_name: repoName,
    days,
  });

  return rows.map((row) => ({
    eventDate: row.event_date,
    starCount: row.star_count,
    totalEvents: row.total_events,
  }));
}

export async function fetchBreakoutRepositories(days = 7, limit = 20): Promise<Repository[]> {
  const rows = await requestJson<BreakoutRepositoryResponse[]>('/intelligence/breakout', {
    days,
    limit,
  });

  return rows.map((row, index) => toBreakoutRepository(row, index));
}

export async function fetchFrameworkRadarSnapshot(): Promise<FrameworkRadarSnapshot> {
  const snapshot = await requestJson<FrameworkRadarSnapshotResponse>('/intelligence/framework-radar');

  return {
    generatedAt: snapshot.generated_at,
    frameworks: snapshot.frameworks.map(toFrameworkRadarItem),
    winners: snapshot.winners,
    warnings: snapshot.warnings,
  };
}

export async function fetchNewsImpactEvents(): Promise<NewsImpactEvent[]> {
  const rows = await requestJson<NewsImpactEventResponse[]>('/intelligence/news-impact');

  return rows.map(toNewsImpactEvent);
}

export async function fetchWeeklyBriefSnapshot(): Promise<WeeklyBriefSnapshot> {
  const snapshot = await requestJson<WeeklyBriefSnapshotResponse>('/intelligence/weekly-brief/latest');

  return {
    briefId: snapshot.brief_id,
    publishedAt: snapshot.published_at,
    title: snapshot.title,
    subtitle: snapshot.subtitle,
    pillars: snapshot.pillars.map((pillar) => ({
      pillarNumber: pillar.pillar_number,
      title: pillar.title,
      description: pillar.description,
    })),
    summaryChartData: snapshot.summary_chart_data.map(toWeeklyBriefChartPoint),
    evidenceSpotlightTitle: snapshot.evidence_spotlight_title,
    evidenceSpotlightBody: snapshot.evidence_spotlight_body,
    evidenceSpotlightBadge: snapshot.evidence_spotlight_badge,
    regionalIndicators: snapshot.regional_indicators.map((indicator) => ({
      region: indicator.region,
      status: indicator.status,
      activePercentage: indicator.active_percentage,
    })),
    authors: snapshot.authors,
    disclaimer: snapshot.disclaimer,
  };
}

export { API_BASE_URL };
