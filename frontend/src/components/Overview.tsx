import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  TrendingUp, 
  Cpu, 
  Activity, 
  ShieldAlert, 
  Radio, 
  ArrowRight, 
  Users, 
  GitBranch, 
  Database,
  Layers,
  Sparkles,
  Command,
  Maximize2,
  Star,
  Trophy
} from 'lucide-react';

import type { DashboardSnapshot } from '../types';

interface OverviewProps {
  data: DashboardSnapshot | null;
  isLoading: boolean;
  onNavigate: (tab: string) => void;
}

function formatNumber(value: number | undefined): string {
  return typeof value === 'number' ? value.toLocaleString() : '--';
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'Crossed this week';
  }
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    timeZone: 'UTC',
  });
}

export const Overview: React.FC<OverviewProps> = ({ data, isLoading, onNavigate }) => {
  const [logs, setLogs] = useState<string[]>([
    'Initializing Stratega telemetry pipeline...',
    'Loading live GitHub dashboard snapshot...',
    'Checking ClickHouse and Parquet availability...',
    'Preparing breakout repository telemetry...',
  ]);

  const topStarredRepos = data?.topStarredRepos ?? data?.topRepos ?? [];
  const weeklyStarIncreases = data?.weeklyStarIncreases ?? data?.trendingRepos ?? [];
  const newTenKRepos = data?.newTenKRepos ?? [];
  const leadingRepo = weeklyStarIncreases[0] ?? topStarredRepos[0] ?? null;
  const latestEvent = data?.latestEvents[0] ?? null;
  const rotationTopic = data?.topicRotation[0] ?? null;
  const pipelineStatus = data?.pipelineStatus?.status ?? 'loading';

  useEffect(() => {
    const rawFeed = [
      leadingRepo
        ? `Detected breakout velocity on ${leadingRepo.fullName}: ${leadingRepo.velocityChange}`
        : 'Awaiting breakout ranking from backend analytics...',
      latestEvent
        ? `Latest event ${latestEvent.eventType} observed on ${latestEvent.repoName}`
        : 'Waiting for fresh event ingestion from ClickHouse...',
      rotationTopic
        ? `Topic rotation shows ${rotationTopic.title} at ${rotationTopic.growth}`
        : 'Topic rotation data is still compiling...',
      `Pipeline status classified as ${pipelineStatus}`,
    ];

    const interval = setInterval(() => {
      const randomLine = rawFeed[Math.floor(Math.random() * rawFeed.length)];
      setLogs(prev => {
        const next = [...prev, `[${new Date().toLocaleTimeString()}] ${randomLine}`];
        if (next.length > 8) next.shift();
        return next;
      });
    }, 4500);

    return () => clearInterval(interval);
  }, [latestEvent, leadingRepo, pipelineStatus, rotationTopic]);

  return (
    <div className="space-y-20 pb-20 overflow-hidden font-sans">
      
      {/* 1. HERO SECTION */}
      <section className="relative pt-12 pb-24 md:py-32 flex flex-col items-center text-center px-4">
        {/* Ambient Fine Light Grid Background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] opacity-70 pointer-events-none" />
        
        {/* Glowing Emerald Spotlight */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-450/5 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        
        {/* Micro-badge */}
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-mono tracking-wider uppercase mb-6 font-semibold shadow-sm"
        >
          <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-600" />
          {isLoading ? 'Loading Live Signal Intelligence' : `Live Signal Intelligence: ${pipelineStatus}`}
        </motion.div>

        {/* Hero Title with deep black/charcoal color */}
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 max-w-4xl"
        >
          See AI adoption before it becomes{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500 font-extrabold">
            obvious.
          </span>
        </motion.h1>

        {/* Hero Subtitle */}
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-slate-500 text-lg sm:text-xl max-w-2xl mt-6 leading-relaxed font-medium"
        >
          Stratega turns your GitHub ingestion pipeline into a live operator dashboard, surfacing breakout repositories, ingestion health, and ecosystem rotation from the FastAPI backend.
        </motion.p>

        {/* CTAs */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 mt-10 z-10"
        >
          <button 
            onClick={() => onNavigate('breakout')}
            className="px-8 py-4 rounded-lg bg-emerald-500 hover:bg-emerald-450 text-slate-950 hover:text-black font-semibold transition-all group flex items-center justify-center gap-2 cursor-pointer shadow-md active:scale-[0.98]"
            id="hero-cta-primary"
          >
            Access Live Signal Screener
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 text-slate-950" />
          </button>
          
        </motion.div>
      </section>

      {/* 2. LIVE TELEMETRY LOG / WORKSPACE MOCKUP WITH FLOATING CARDS */}
      <section className="max-w-6xl mx-auto px-4 relative">
        <div className="absolute inset-x-0 -top-12 h-24 bg-gradient-to-b from-white to-transparent pointer-events-none z-10" />

        <div className="relative">
          {/* Mockup Terminal with rounded corners and overflow hidden */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl relative">
            
            {/* Header Controls */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-900/60 border-b border-slate-800/80">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-500/60" />
                <span className="w-3 h-3 rounded-full bg-amber-500/60" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/60" />
                <span className="text-slate-500 text-xs font-mono ml-4 truncate max-w-[200px] sm:max-w-none">
                  stratega@telemetry:~ (raw_stream.sh)
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 px-2.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[10px] uppercase">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping mr-1" />
                  Live Ingress
                </div>
                <Maximize2 className="w-3.5 h-3.5 text-slate-500 hover:text-slate-350 cursor-pointer" />
              </div>
            </div>

            <div className="p-6 font-mono text-xs sm:text-sm text-slate-350 bg-slate-950/90 relative min-h-[220px] max-h-[300px] overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {logs.map((log, i) => (
                  <motion.div
                    key={log + i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                    className={`${log.includes('Signal alert') || log.includes('Velocity') ? 'text-teal-400 font-semibold' : log.includes('Warning') ? 'text-amber-400' : 'text-slate-400'}`}
                  >
                    <span className="text-slate-500 mr-2">&gt;&gt;</span>
                    {log}
                  </motion.div>
                ))}
              </AnimatePresence>
              <div className="w-1.5 h-4 bg-slate-400 animate-pulse inline-block mt-1 align-middle" />
            </div>

          </div>

          {/* Floating Overlap Cards placed outside of overflow-hidden div container */}
          <div className="absolute -bottom-10 right-4 sm:right-12 max-w-sm bg-slate-900 border border-emerald-500/30 p-4 rounded-xl shadow-2xl flex items-start gap-3 backdrop-blur-md z-20">
            <div className="p-2 bg-emerald-500/10 rounded border border-emerald-500/20 text-emerald-400 flex-shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <div className="text-white text-xs font-semibold uppercase font-display tracking-wide">
                Detected Signal BREAKOUT
              </div>
              <p className="text-slate-400 text-xs">
                {leadingRepo
                  ? `${leadingRepo.fullName} is the current breakout leader with ${leadingRepo.velocityChange} weekly star momentum.`
                  : 'Breakout ranking will appear here as soon as the dashboard API returns data.'}
              </p>
              <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800 font-mono text-[10px] text-slate-400">
                <span>Velocity Index: <strong className="text-emerald-400">{leadingRepo?.velocityIndex ?? '--'}/10</strong></span>
                <span>•</span>
                <span>Active Contributors: <strong className="text-emerald-400">{leadingRepo?.activeContributors ?? '--'}</strong></span>
              </div>
            </div>
          </div>
          
          <div className="absolute -top-8 -left-2 sm:left-12 max-w-sm bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-2xl flex items-start gap-3 backdrop-blur-md z-20 hidden md:flex">
            <div className="p-2 bg-indigo-500/10 rounded border border-indigo-500/20 text-indigo-400 flex-shrink-0">
              <Cpu className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <div className="text-white text-xs font-semibold uppercase font-display tracking-wide">
                System Status Shift
              </div>
              <p className="text-slate-400 text-xs">
                {rotationTopic
                  ? `${rotationTopic.title} is currently the fastest accelerating topic in the live dashboard.`
                  : 'Topic rotation intelligence will appear here once the backend returns sector data.'}
              </p>
              <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800 font-mono text-[10px] text-slate-400">
                <span>Confidence: <strong className="text-indigo-400">{rotationTopic?.momentum ?? '--'}%</strong></span>
                <span>•</span>
                <span>Causality Index: <strong className="text-indigo-400">{rotationTopic?.score ?? '--'}</strong></span>
              </div>
            </div>
          </div>
        </div>

        {/* Client Logos Row */}
        <div className="mt-20 border-t border-b border-slate-200 py-8 text-center">
          <div className="text-slate-400 text-xs font-mono uppercase tracking-widest mb-6">
            Institutional Adoption Telemetry Trusted By
          </div>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 opacity-80 hover:opacity-100 transition-opacity">
            <span className="text-slate-800 font-semibold font-display tracking-wider text-sm flex items-center gap-2">
              <Command className="w-4 h-4 text-emerald-600" /> COGNITIVE PARTNERS
            </span>
            <span className="text-slate-800 font-semibold font-display tracking-wider text-sm flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-600" /> ADVISORS IN AI
            </span>
            <span className="text-slate-500 font-semibold font-display tracking-wider text-xs font-mono">
              [VANCE RESEARCH GROUP]
            </span>
            <span className="text-slate-800 font-semibold font-display tracking-wider text-sm flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-600" /> HYPERSCALE CAP
            </span>
          </div>
        </div>
      </section>

      {/* 3. LIVE GITHUB DASHBOARD USE CASES */}
      <section className="max-w-6xl mx-auto px-4 space-y-8">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div className="space-y-2">
            <h2 className="text-xs font-mono text-emerald-600 font-bold uppercase tracking-widest">
              GitHub Dashboard
            </h2>
            <p className="text-2xl sm:text-3xl font-display font-medium text-slate-950">
              Live repository rankings for all-time scale and weekly breakout velocity
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 bg-white border border-slate-200 rounded-full px-4 py-2 w-fit">
            Refreshed: {data?.refreshedAt ? new Date(data.refreshedAt).toLocaleTimeString() : 'loading'}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">All-time most-starred</h3>
                <p className="text-xs text-slate-500 font-mono">Historical GitHub star leaders</p>
              </div>
              <div className="p-2 rounded-lg bg-amber-50 text-amber-600 border border-amber-200">
                <Trophy className="w-5 h-5" />
              </div>
            </div>
            <div className="space-y-3">
              {topStarredRepos.slice(0, 5).map((repo, index) => (
                <a
                  key={`top-starred-${repo.fullName}`}
                  href={repo.repoUrl || undefined}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-xl border border-slate-100 hover:border-amber-200 hover:bg-amber-50/40 p-3 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[10px] font-mono text-slate-400">#{index + 1}</div>
                      <div className="font-semibold text-sm text-slate-900 truncate">{repo.fullName}</div>
                      <div className="text-xs text-slate-500 truncate">{repo.language}</div>
                    </div>
                    <div className="text-right font-mono text-xs text-amber-700 shrink-0">
                      <Star className="w-3.5 h-3.5 inline mr-1" />
                      {formatNumber(repo.starCount)}
                    </div>
                  </div>
                </a>
              ))}
              {topStarredRepos.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  Waiting for all-time repository rankings from the dashboard API.
                </div>
              )}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">Biggest star increases</h3>
                <p className="text-xs text-slate-500 font-mono">Current GMT+7 week growth</p>
              </div>
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200">
                <TrendingUp className="w-5 h-5" />
              </div>
            </div>
            <div className="space-y-3">
              {weeklyStarIncreases.slice(0, 5).map((repo, index) => (
                <a
                  key={`weekly-growth-${repo.fullName}`}
                  href={repo.repoUrl || undefined}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-xl border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/40 p-3 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[10px] font-mono text-slate-400">#{repo.rank || index + 1}</div>
                      <div className="font-semibold text-sm text-slate-900 truncate">{repo.fullName}</div>
                      <div className="text-xs text-slate-500 truncate">{formatNumber(repo.starCount)} total stars</div>
                    </div>
                    <div className="text-right font-mono text-xs text-emerald-700 shrink-0">
                      +{formatNumber(repo.starGain7d)}
                      <div className="text-[10px] text-slate-400">this week</div>
                    </div>
                  </div>
                </a>
              ))}
              {weeklyStarIncreases.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                  Waiting for weekly star growth leaders from repository history.
                </div>
              )}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">New 10k-star repos</h3>
                <p className="text-xs text-slate-500 font-mono">Crossed the milestone this week</p>
              </div>
              <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200">
                <Sparkles className="w-5 h-5" />
              </div>
            </div>
            <div className="space-y-3">
              {newTenKRepos.slice(0, 5).map((repo) => (
                <a
                  key={`ten-k-${repo.fullName}`}
                  href={repo.repoUrl || undefined}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/40 p-3 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-[10px] font-mono text-slate-400">{formatDate(repo.crossedThresholdAt)}</div>
                      <div className="font-semibold text-sm text-slate-900 truncate">{repo.fullName}</div>
                      <div className="text-xs text-slate-500 truncate">
                        {formatNumber(repo.baselineStars)} → {formatNumber(repo.currentStars)} stars
                      </div>
                    </div>
                    <div className="text-right font-mono text-xs text-indigo-700 shrink-0">
                      +{formatNumber(repo.starGain7d)}
                      <div className="text-[10px] text-slate-400">delta</div>
                    </div>
                  </div>
                </a>
              ))}
              {newTenKRepos.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500 leading-relaxed">
                  No repositories crossed 10k stars yet this week. This card will populate automatically when repository history detects a new milestone.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 4. BENTO GRID: SOPHISTICATED SIGNALS */}
      <section className="max-w-6xl mx-auto px-4 space-y-12">
        <div className="text-center md:text-left space-y-2">
          <h2 className="text-xs font-mono text-emerald-600 font-bold uppercase tracking-widest">
            Strategic Infrastructure
          </h2>
          <p className="text-2xl sm:text-3xl font-display font-medium text-slate-950">
            Our Sophisticated Signals Dashboard Suite
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Bento Card 1 */}
          <div className="col-span-1 md:col-span-2 bg-white border border-slate-200 hover:border-slate-350 hover:shadow-md p-6 rounded-2xl flex flex-col justify-between transition-all group relative overflow-hidden shadow-sm">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl group-hover:bg-emerald-500/8 transition-all" />
            <div className="space-y-4">
              <div className="p-3 bg-emerald-50 border border-emerald-200/60 text-emerald-600 rounded-lg w-fit">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-display font-semibold text-slate-900 group-hover:text-emerald-700 transition-colors">
                  Breakout Detector
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed max-w-lg">
                  Scurry GitHub core code repositories. This tool extracts early developer migrations toward novel architectures before they hit blogs, newsletters, or tech news.
                </p>
              </div>
            </div>
            <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Includes Sparkline & Hype-risk filters</span>
              <button 
                onClick={() => onNavigate('breakout')}
                className="text-emerald-600 hover:text-emerald-700 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 cursor-pointer font-semibold font-mono"
              >
                Open Screener <ArrowRight className="w-3 h-3 text-emerald-600" />
              </button>
            </div>
          </div>

          {/* Bento Card 2 */}
          <div className="bg-white border border-slate-200 hover:border-slate-350 hover:shadow-md p-6 rounded-2xl flex flex-col justify-between transition-all group relative overflow-hidden shadow-sm">
            <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-2xl group-hover:bg-indigo-500/8 transition-all" />
            <div className="space-y-4">
              <div className="p-3 bg-indigo-50 border border-indigo-200/60 text-indigo-600 rounded-lg w-fit">
                <Layers className="w-6 h-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-display font-semibold text-slate-900 group-hover:text-indigo-700 transition-colors">
                  Ecosystem Rotation
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  Map shifting software attention. Observe standard semantic search vectors losing developer focus while active orchestrations and model reasoning workflows spike in activity.
                </p>
              </div>
            </div>
            <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Live Attention flow map</span>
              <button 
                onClick={() => onNavigate('ecosystems')}
                className="text-indigo-600 hover:text-indigo-700 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 cursor-pointer font-semibold font-mono"
              >
                Track Shifts <ArrowRight className="w-3 h-3 text-indigo-650" />
              </button>
            </div>
          </div>

          {/* Bento Card 3 */}
          <div className="bg-white border border-slate-200 hover:border-slate-350 hover:shadow-md p-6 rounded-2xl flex flex-col justify-between transition-all group relative overflow-hidden shadow-sm">
            <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl group-hover:bg-amber-500/8 transition-all" />
            <div className="space-y-4">
              <div className="p-3 bg-amber-50 border border-amber-200/60 text-amber-600 rounded-lg w-fit">
                <Activity className="w-6 h-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-display font-semibold text-slate-900 group-hover:text-amber-700 transition-colors">
                  News-to-Code Impact
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  Anchor press announcements to technical commits. Track how many hours pass before a news release triggers novel codebase code changes.
                </p>
              </div>
            </div>
            <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Causality confidence tracker</span>
              <button 
                onClick={() => onNavigate('newsImpact')}
                className="text-amber-600 hover:text-amber-705 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 cursor-pointer font-semibold font-mono"
              >
                View Timeline <ArrowRight className="w-3 h-3 text-amber-600" />
              </button>
            </div>
          </div>

        </div>
      </section>

      {/* 4. THE INTELLIGENCE PIPELINE */}
      <section className="max-w-6xl mx-auto px-4 space-y-12">
        <div className="text-center space-y-2">
          <h2 className="text-xs font-mono text-emerald-600 font-semibold uppercase tracking-widest">
            Processing Core
          </h2>
          <p className="text-2xl sm:text-3xl font-display font-medium text-slate-950">
            The Stratega Intelligence Pipeline
          </p>
        </div>

        {/* Pipeline Line Flow */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          
          {/* Connector Line overlay (for md screen) */}
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500/10 via-emerald-500/40 to-emerald-500/10 -translate-y-1/2 hidden md:block z-0 pointer-events-none" />

          {/* Pipeline Step 1 */}
          <div className="bg-white border border-slate-200 shadow-sm p-6 rounded-xl relative z-10 space-y-4">
              <span className="absolute -top-4 left-6 py-1 px-2.5 bg-slate-50 border border-slate-200 text-slate-600 rounded text-xs font-mono font-bold shadow-sm">
              01 / SOURCE INGEST
            </span>
            <div className="flex items-center justify-between pt-2">
              <span className="text-slate-900 font-display font-semibold">Raw Repository Streams</span>
              <div className="px-2 py-0.5 rounded bg-emerald-50 border border-emerald-150 text-emerald-700 text-[10px] font-mono font-semibold">
                {data?.latestEvents.length ?? 0} latest sampled
              </div>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              The backend ingests GitHub events into Kafka, persists them into ClickHouse and Parquet, and exposes the newest samples through the dashboard API.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-500 pt-2">
              <span className="flex items-center gap-1"><Users className="w-3 h-3 text-emerald-600" /> Contributor Logs</span>
              <span className="flex items-center gap-1"><GitBranch className="w-3 h-3 text-emerald-600" /> Commit Telemetry</span>
            </div>
          </div>

          {/* Pipeline Step 2 */}
          <div className="bg-white border border-slate-200 shadow-sm p-6 rounded-xl relative z-10 space-y-4">
            <span className="absolute -top-4 left-6 py-1 px-2.5 bg-slate-50 border border-slate-200 text-slate-600 rounded text-xs font-mono font-bold shadow-sm">
              02 / COGNITIVE FILTER
            </span>
            <div className="flex items-center justify-between pt-2">
              <span className="text-slate-900 font-display font-semibold">Pattern Processing</span>
              <div className="px-2 py-0.5 rounded bg-amber-50 border border-amber-150 text-amber-700 text-[10px] font-mono font-semibold">
                {pipelineStatus}
              </div>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              Dashboard queries summarize top repositories, trending movers, topic rotation, and pipeline health from the cleaned backend flow.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-500 pt-2">
              <span className="flex items-center gap-1"><Activity className="w-3 h-3 text-amber-600" /> Velocity Ranking</span>
              <span className="flex items-center gap-1"><Database className="w-3 h-3 text-amber-600" /> Noise Filtration</span>
            </div>
          </div>

          {/* Pipeline Step 3 */}
          <div className="bg-white border border-slate-200 shadow-sm p-6 rounded-xl relative z-10 space-y-4">
            <span className="absolute -top-4 left-6 py-1 px-2.5 bg-slate-50 border border-slate-200 text-slate-600 rounded text-xs font-mono font-bold shadow-sm">
              03 / SIGNAL DISPATCH
            </span>
            <div className="flex items-center justify-between pt-2">
              <span className="text-slate-900 font-display font-semibold">Market Intelligence</span>
              <div className="px-2 py-0.5 rounded bg-indigo-50 border border-indigo-150 text-indigo-700 text-[10px] font-mono font-semibold">
                {leadingRepo ? leadingRepo.velocityChange : 'Pending'}
              </div>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              The frontend now consumes backend APIs directly for the core dashboard while preserving research-oriented presentation views for curated analysis.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-500 pt-2">
              <span className="flex items-center gap-1"><ShieldAlert className="w-3 h-3 text-indigo-600" /> Causality Index</span>
              <span className="flex items-center gap-1"><Layers className="w-3 h-3 text-indigo-600" /> Core Editorial</span>
            </div>
          </div>

        </div>
      </section>

      {/* 5. CALL TO ACTION WITH DEEP CANVAS BACKDROP */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="relative rounded-3xl bg-slate-900 overflow-hidden border border-slate-800 p-8 sm:p-12 md:p-16 flex flex-col md:flex-row items-center justify-between gap-10 shadow-xl">
          
          {/* Neon Radial Accent */}
          <div className="absolute -right-24 -bottom-24 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="space-y-4 max-w-xl text-center md:text-left">
            <h2 className="font-display font-bold text-2xl sm:text-3xl md:text-4xl text-white">
              Secure your edge in the AI economy.
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              Receive live Slack/Telegram alerts on emerging breakout repos, daily technical intelligence digests, and macro advisory briefs under Alistair Vance directly.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            <input 
              type="email" 
              placeholder="Enter institutional email"
              className="px-4 py-3 bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-emerald-500 rounded-lg text-white text-sm font-mono focus:outline-none w-full sm:w-64"
            />
            <button 
              onClick={() => alert("Subscription request submitted successfully! In a real system, this connects to the corporate email pipeline.")}
              className="px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 hover:text-black font-semibold rounded-lg text-sm flex items-center justify-center gap-2 whitespace-nowrap cursor-pointer active:scale-95 transition-all w-full sm:w-auto"
            >
              Request Access
            </button>
          </div>

        </div>
      </section>

    </div>
  );
};
