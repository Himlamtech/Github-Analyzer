import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  TrendingUp, 
  Search, 
  ShieldCheck, 
  Activity, 
  Filter, 
  ChevronRight, 
  Star, 
  User, 
  Calendar, 
  GitCommit, 
  LineChart, 
  X,
  Plus,
  ArrowRight,
  Sparkles,
  Info
} from 'lucide-react';

import { useRepoTimeseries } from '../hooks/useRepoTimeseries';
import { Repository } from '../types';

const generateSparklinePath = (sparkline: number[], width: number, height: number): string => {
  if (!sparkline || sparkline.length === 0) return '';
  const minVal = Math.min(...sparkline);
  const maxVal = Math.max(...sparkline);
  const valRange = maxVal - minVal || 1;
  const padding = 2;

  const points = sparkline.map((val, idx) => {
    const x = (idx / (sparkline.length - 1)) * (width - 2 * padding) + padding;
    const y = height - ((val - minVal) / valRange) * (height - 2 * padding) - padding;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return `M ${points.join(' L ')}`;
};

interface BreakoutDetectorProps {
  isLoading: boolean;
  repositories: Repository[];
}

export const BreakoutDetector: React.FC<BreakoutDetectorProps> = ({ isLoading, repositories }) => {
  const [selectedSector, setSelectedSector] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const { points: repoTimeseries, isLoading: isTimeseriesLoading } = useRepoTimeseries(
    selectedRepo?.fullName ?? null,
  );

  const sectors = ['All', ...new Set(repositories.map((repo) => repo.sector))];
  const topRepo = repositories[0] ?? null;
  const highestVelocityRepo = [...repositories].sort((left, right) => right.velocityIndex - left.velocityIndex)[0] ?? null;
  const hypeRiskScore = repositories.length
    ? Math.round(
        repositories.reduce((total, repo) => {
          const scoreByRisk: Record<Repository['hypeRisk'], number> = {
            Low: 20,
            Moderate: 48,
            Elevated: 72,
            Extreme: 91,
          };
          return total + scoreByRisk[repo.hypeRisk];
        }, 0) / repositories.length,
      )
    : 0;

  const getShortSectorName = (sec: string) => {
    if (sec === 'All') return 'All Sectors';
    if (sec.length > 18) return `${sec.slice(0, 18)}...`;
    return sec;
  };

  const filteredRepos = repositories.filter(repo => {
    const matchesSector = selectedSector === 'All' || repo.sector === selectedSector;
    const matchesSearch = repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          repo.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          repo.sector.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSector && matchesSearch;
  });

  return (
    <div className="space-y-6 pb-20 font-sans relative">
      
      {/* Page Title & Backlinks */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-display font-medium text-slate-900 tracking-tight flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-emerald-600" /> 
            Breakout Detector: Early Signal Identification
          </h1>
          <p className="text-slate-600 text-sm">
            Filtering code deployments to isolate durable adoption speed curves before mainstream hype risk rises.
          </p>
        </div>
        
        {/* Active Indicators */}
          <div className="flex items-center gap-2 bg-white border border-slate-250/80 rounded-lg p-1.5 px-3 self-start md:self-auto font-mono text-xs text-slate-605 select-none shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{isLoading ? 'Compiling breakout index...' : 'Last index compiled from live API snapshot'}</span>
          </div>
      </div>

      {/* THREE SCORE CARDS / HIGH-LEVEL METRICS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        
        {/* Stat Card 1 */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center justify-between group shadow-sm">
          <div className="space-y-1">
            <span className="text-slate-500 text-xs font-mono uppercase tracking-wider block">
              Total Active Repos Managed
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-display text-slate-900">{repositories.length}</span>
              <span className="text-emerald-600 text-xs font-mono font-medium">Live snapshot</span>
            </div>
          </div>
          <div className="p-3 bg-emerald-50 border border-emerald-100 text-emerald-600 rounded-lg group-hover:scale-105 transition-transform">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        {/* Stat Card 2 */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center justify-between group shadow-sm">
          <div className="space-y-1">
            <span className="text-slate-500 text-xs font-mono uppercase tracking-wider block">
              Highest Velocity Weekly Spark
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold font-display text-emerald-600">{highestVelocityRepo?.velocityChange ?? '--'}</span>
              <span className="text-slate-500 text-xs font-mono truncate max-w-[110px] ml-1">
                ({highestVelocityRepo?.name ?? 'n/a'})
              </span>
            </div>
          </div>
          <div className="p-3 bg-emerald-50 border border-emerald-100 text-emerald-600 rounded-lg group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>

        {/* Stat Card 3 */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl flex items-center justify-between group shadow-sm">
          <div className="space-y-1">
            <span className="text-slate-500 text-xs font-mono uppercase tracking-wider block">
              Global AI Hype Risk index
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-display text-amber-600 font-semibold">{topRepo?.hypeRisk ?? 'Unknown'}</span>
              <span className="text-slate-500 text-xs font-mono">Index {hypeRiskScore}/100</span>
            </div>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-100 text-amber-605 text-amber-600 rounded-lg group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

      </div>

      {/* CORE WORKSPACE: COMMAND SIDEBAR + PRIMARY SCREEN */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Interactive Left Column Sidebar */}
        <div className="col-span-1 bg-white border border-slate-200 p-4 rounded-xl space-y-6 shadow-sm">
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-slate-450 uppercase tracking-widest block font-bold">
              Command Center
            </span>
            <p className="text-slate-905 text-sm font-semibold font-display">Sector Focus</p>
          </div>
          
          <nav className="space-y-1.5 list-none">
            {sectors.map((sector) => {
              const count = sector === 'All' 
                ? repositories.length 
                : repositories.filter((repo) => repo.sector === sector).length;
              const isSelected = selectedSector === sector;
              
              return (
                <button
                  key={sector}
                  onClick={() => setSelectedSector(sector)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center justify-between 
                    ${isSelected 
                      ? 'bg-emerald-50 border border-emerald-200 text-emerald-700 shadow-[0_0_10px_rgba(16,185,129,0.03)]' 
                      : 'hover:bg-slate-50 hover:text-slate-900 text-slate-600 border border-transparent'
                    }`}
                >
                  <span className="truncate pr-2">{sector === 'All' ? 'All Intelligence' : sector}</span>
                  <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded-full ${isSelected ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </nav>

          <div className="pt-4 border-t border-slate-150 space-y-3">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-750 bg-emerald-50/50 p-2 px-2.5 rounded border border-emerald-200/50">
              <Info className="w-3.5 h-3.5 flex-shrink-0 text-emerald-600" />
              <span>Screener auto-refreshes on commits detected in upstream repositories.</span>
            </div>
            
            {/* Weekly preview card link */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 block transition-all shadow-sm">
              <span className="text-slate-500 text-[9px] font-mono uppercase tracking-widest block mb-1">
                Live API focus
              </span>
              <p className="text-slate-900 text-xs font-display font-medium">
                This screener is powered by `/intelligence/breakout` and `/dashboard/repo-timeseries`.
              </p>
              <div className="flex items-center gap-1 mt-2 font-mono text-[10px] text-slate-500">
                <span>FastAPI-backed analytics</span>
              </div>
            </div>
          </div>
        </div>

        {/* Massive Screen View on Right Side (Table list grid) */}
        <div className="col-span-1 lg:col-span-3 space-y-4">
          
          {/* Header Action Row */}
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-center bg-white p-3 rounded-lg border border-slate-200 shadow-sm animate-fade-in-up">
            {/* Search Input */}
            <div className="relative w-full sm:w-72">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 pointer-events-none">
                <Search className="w-4 h-4" />
              </span>
              <input 
                type="text" 
                placeholder="Search index assets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 focus:bg-white rounded-lg text-xs placeholder-slate-450 border border-slate-200 hover:border-slate-300 focus:border-emerald-500 text-slate-900 focus:outline-none transition-all shadow-inner"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-700"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Segment filters matching dashboard mock Section 3 */}
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto scrollbar-none">
              <Filter className="w-3.5 h-3.5 text-slate-405 text-slate-400 flex-shrink-0" />
              {sectors.slice(0, 4).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setSelectedSector(tab)}
                  className={`px-3 py-1.5 rounded-md text-[10px] font-mono whitespace-nowrap cursor-pointer transition-all ${selectedSector === tab ? 'bg-slate-100 text-slate-900 border border-slate-200 font-semibold' : 'text-slate-500 border border-transparent hover:text-slate-900 hover:bg-slate-50'}`}
                >
                  {getShortSectorName(tab)}
                </button>
              ))}
            </div>
          </div>

          {/* Sparkline & Table List Container */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 font-mono text-[10px] text-slate-500 uppercase tracking-widest">
                    <th className="py-4 px-4 font-semibold">Repository</th>
                    <th className="py-4 px-4 font-semibold hidden md:table-cell">Sector</th>
                    <th className="py-4 px-4 font-semibold text-center">Velocity Index</th>
                    <th className="py-4 px-4 font-semibold text-center hidden sm:table-cell">7d Trend</th>
                    <th className="py-4 px-4 font-semibold text-center">Momentum Durability</th>
                    <th className="py-4 px-4 font-semibold text-center font-bold">Hype Risk</th>
                    <th className="py-4 px-4 text-right pr-6"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {filteredRepos.length > 0 ? (
                    filteredRepos.map((repo) => {
                      const trendUp = repo.sparkline[repo.sparkline.length - 1] > repo.sparkline[0];
                      
                      return (
                        <tr 
                          key={repo.id}
                          onClick={() => setSelectedRepo(repo)}
                          className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                        >
                          {/* Repository Info */}
                          <td className="py-4 px-4 space-y-1 max-w-[180px] sm:max-w-none">
                            <div className="font-semibold text-slate-900 font-display text-sm group-hover:text-emerald-600 transition-colors flex items-center gap-1.5 flex-wrap">
                              <span className="text-slate-400 font-normal">{repo.owner} /</span>
                              <span>{repo.name}</span>
                            </div>
                            <p className="text-slate-500 text-xs truncate max-w-[200px] sm:max-w-sm">
                              {repo.description}
                            </p>
                          </td>

                          {/* Sector Tag */}
                          <td className="py-4 px-4 hidden md:table-cell">
                            <span className="px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-600 text-[10px] font-medium">
                              {repo.sector}
                            </span>
                          </td>

                          {/* Index Value & Change */}
                          <td className="py-4 px-4 text-center">
                            <div className="flex flex-col items-center">
                              <span className="font-mono font-bold text-sm text-slate-800">
                                {repo.velocityIndex}
                              </span>
                              <span className="font-mono text-[10px] text-emerald-600 font-medium">
                                {repo.velocityChange}
                              </span>
                            </div>
                          </td>

                          {/* Animated Sparkline Column */}
                          <td className="py-4 px-4 text-center hidden sm:table-cell">
                            <div className="flex items-center justify-center">
                              <svg className="w-20 h-8 overflow-visible" viewBox="0 0 80 24">
                                <motion.path
                                  key={`${repo.id}-${JSON.stringify(repo.sparkline)}`}
                                  d={generateSparklinePath(repo.sparkline, 80, 24)}
                                  fill="none"
                                  stroke={trendUp ? '#059669' : '#d97706'}
                                  strokeWidth="2"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  initial={{ pathLength: 0 }}
                                  animate={{ pathLength: 1 }}
                                  transition={{ duration: 1.1, ease: 'easeInOut' }}
                                />
                                <circle 
                                  cx="78" 
                                  cy={24 - ((repo.sparkline[repo.sparkline.length - 1] - Math.min(...repo.sparkline)) / (Math.max(...repo.sparkline) - Math.min(...repo.sparkline) || 1)) * 20 - 2} 
                                  r="2.5" 
                                  fill={trendUp ? '#059669' : '#d97706'} 
                                />
                              </svg>
                            </div>
                          </td>

                          {/* Durable Momentum Progress */}
                          <td className="py-4 px-4">
                            <div className="flex flex-col items-center gap-1 max-w-[124px] mx-auto">
                              <div className="flex items-center justify-between w-full font-mono text-[9px] text-slate-500">
                                <span className="opacity-85 font-mono">DURABILITY</span>
                                <span className="text-slate-800 font-bold">{repo.durableMomentum}%</span>
                              </div>
                              <div className="w-full bg-slate-100 h-1.5 border border-slate-200/80 rounded overflow-hidden">
                                <div 
                                  className="bg-emerald-500 h-full rounded transition-all" 
                                  style={{ width: `${repo.durableMomentum}%` }}
                                />
                              </div>
                            </div>
                          </td>

                          {/* Hype Risk level badge */}
                          <td className="py-4 px-4 text-center">
                            <span className={`inline-block px-2 py-0.5 rounded text-[9px] font-mono font-medium border uppercase tracking-wider
                              ${repo.hypeRisk === 'Low' 
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-700' 
                                : repo.hypeRisk === 'Moderate'
                                  ? 'bg-amber-55 border-amber-200 text-amber-700 bg-amber-50'
                                  : 'bg-rose-50 border-rose-200 text-rose-700'
                              }`}
                            >
                              {repo.hypeRisk}
                            </span>
                          </td>

                          {/* Arrow link trigger */}
                          <td className="py-4 px-4 text-right pr-6">
                            <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-0.5 transition-all inline-block" />
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-500 font-mono text-xs">
                        {isLoading ? 'Loading repositories from backend...' : 'No repositories found matching sector / search filters.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Interactive Sparklines preview chart widget as Screen 3 */}
          <div className="bg-white border border-slate-200 p-5 rounded-xl space-y-4 shadow-sm animate-fade-in-up">
            <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest block font-bold">
              Live Contributor Energy Wave
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in-up">
              <div className="bg-slate-50 p-4 border border-slate-200 rounded-lg flex items-center justify-between shadow-inner">
                <div>
                  <span className="text-slate-500 text-[10px] font-mono uppercase block">browser-use wave</span>
                  <p className="text-slate-900 text-sm font-semibold mt-1">Velocity Score {topRepo?.velocityIndex ?? '--'}</p>
                  <span className="font-mono text-xs text-emerald-600">{topRepo?.velocityChange ?? 'Waiting for API data'}</span>
                </div>
                {/* SVG Mini sparkline */}
                <svg className="w-24 h-10 text-emerald-600" viewBox="0 0 100 30">
                  <path 
                    d="M 5,25 Q 20,20 40,24 T 70,8 T 95,5" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2.5" 
                  />
                  <circle cx="95" cy="5" r="3" fill="currentColor" />
                </svg>
              </div>

              <div className="bg-slate-50 p-4 border border-slate-200 rounded-lg flex items-center justify-between shadow-inner">
                <div>
                  <span className="text-slate-500 text-[10px] font-mono uppercase block">runner-up wave</span>
                  <p className="text-slate-900 text-sm font-semibold mt-1">Velocity Score {repositories[1]?.velocityIndex ?? '--'}</p>
                  <span className="font-mono text-xs text-emerald-600">{repositories[1]?.velocityChange ?? 'Waiting for API data'}</span>
                </div>
                {/* SVG Mini sparkline */}
                <svg className="w-24 h-10 text-emerald-600" viewBox="0 0 100 30">
                  <path 
                    d="M 5,28 Q 20,28 40,24 T 70,14 T 95,10" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2.5" 
                  />
                  <circle cx="95" cy="10" r="3" fill="currentColor" />
                </svg>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* DETAILED OVERLAY PANEL: SLIDES OUT FROM RIGHT */}
      <AnimatePresence>
        {selectedRepo && (
          <>
            {/* Backdrop Blur overlay */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-40 cursor-pointer"
              onClick={() => setSelectedRepo(null)}
            />

            {/* Sidebar drawer content */}
            <motion.div 
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 right-0 w-full sm:max-w-md bg-white border-l border-slate-200 shadow-2xl z-50 p-6 flex flex-col justify-between overflow-y-auto"
            >
              <div className="space-y-6">
                
                {/* Drawer Header */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-mono text-emerald-600 uppercase tracking-widest font-bold">
                      Deep Telemetry Profile
                    </span>
                    <h2 className="text-lg font-display text-slate-900 font-bold">
                      {selectedRepo.owner}/{selectedRepo.name}
                    </h2>
                  </div>
                  <button 
                    onClick={() => setSelectedRepo(null)}
                    className="p-1 px-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-650 hover:text-slate-900 transition-all cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Scope Description */}
                <div className="space-y-2">
                  <span className="text-slate-500 text-[10px] font-mono uppercase tracking-widest font-bold block">
                    Telemetry Scope
                  </span>
                  <p className="text-slate-800 text-xs leading-relaxed bg-slate-50 p-3.5 border border-slate-200/60 rounded-lg">
                    {selectedRepo.description}
                  </p>
                </div>

                {/* Score indicators */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg font-mono shadow-inner">
                    <span className="text-slate-500 text-[10px] uppercase block font-semibold">Velocity Score</span>
                    <strong className="text-emerald-600 text-lg">{selectedRepo.velocityIndex} / 10</strong>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg font-mono shadow-inner">
                    <span className="text-slate-500 text-[10px] uppercase block font-semibold">Durable momentum</span>
                    <strong className="text-emerald-600 text-lg">{selectedRepo.durableMomentum}%</strong>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg font-mono shadow-inner">
                    <span className="text-slate-500 text-[10px] uppercase block font-semibold">Confidence</span>
                    <strong className="text-emerald-600 text-lg">{selectedRepo.confidenceScore.toFixed(1)}</strong>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg font-mono shadow-inner">
                    <span className="text-slate-500 text-[10px] uppercase block font-semibold">Breakout score</span>
                    <strong className="text-emerald-600 text-lg">{selectedRepo.breakoutScore.toFixed(1)}</strong>
                  </div>
                </div>

                {/* Advanced Telemetry Stats */}
                <div className="space-y-3.5 pt-2">
                  <span className="text-slate-500 text-[10px] font-mono uppercase block font-bold">Interactive Indicators</span>
                  
                  <div className="space-y-2">
                    {/* Stat Row 1 */}
                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><Star className="w-3.5 h-3.5 text-slate-400" /> Star Count</span>
                      <strong className="text-slate-800">{(selectedRepo.starCount / 1000).toFixed(1)}k</strong>
                    </div>

                    {/* Stat Row 2 */}
                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-slate-400" /> Active Contributors</span>
                      <strong className="text-slate-800">{selectedRepo.activeContributors}</strong>
                    </div>

                    {/* Stat Row 3 */}
                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><GitCommit className="w-3.5 h-3.5 text-slate-400" /> 24h Commit Stream</span>
                      <strong className="text-emerald-600">+{selectedRepo.commits24h} commits</strong>
                    </div>

                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-slate-400" /> 7d Star Gain</span>
                      <strong className="text-slate-800">+{selectedRepo.starGain7d}</strong>
                    </div>

                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><ArrowRight className="w-3.5 h-3.5 text-slate-400" /> Vs Previous Window</span>
                      <strong className={`${selectedRepo.starGainVsPreviousWindow >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {selectedRepo.starGainVsPreviousWindow >= 0 ? '+' : ''}
                        {selectedRepo.starGainVsPreviousWindow}
                      </strong>
                    </div>

                    {/* Stat Row 4 */}
                    <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100 font-mono">
                      <span className="text-slate-600 flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 text-slate-400" /> Detection Date</span>
                      <strong className="text-slate-500">{new Date(selectedRepo.lastPushedAt).toLocaleDateString()}</strong>
                    </div>
                  </div>
                </div>

                {/* Spark / Growth Curve diagram */}
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3 font-mono text-[11px] shadow-inner">
                  <span className="text-slate-500 text-[10px] uppercase block font-semibold animate-pulse">Durable Growth Curve</span>
                  <div className="h-28 flex items-end justify-between gap-1.5 pt-4">
                    {(repoTimeseries.length > 0 ? repoTimeseries.map((point) => point.starCount) : selectedRepo.sparkline).map((val, idx) => (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                        <div 
                          className="w-full bg-emerald-500/20 hover:bg-emerald-500/60 rounded-sm transition-all relative group cursor-pointer"
                          style={{ height: `${(val / Math.max(...(repoTimeseries.length > 0 ? repoTimeseries.map((point) => point.starCount) : selectedRepo.sparkline), 1)) * 80}px` }}
                        >
                          {/* Hover Tooltip */}
                          <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-900 border border-slate-800 px-1 py-0.5 rounded text-[8px] opacity-0 group-hover:opacity-100 transition-opacity text-white pointer-events-none shadow-md">
                            {val}
                          </div>
                        </div>
                        <span className="text-[8px] text-slate-400">{repoTimeseries[idx]?.eventDate?.slice(5) ?? `${idx + 1}d`}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {isTimeseriesLoading
                      ? 'Loading repository time-series from backend...'
                      : repoTimeseries.length > 0
                        ? 'Chart sourced from /dashboard/repo-timeseries.'
                        : 'Fallback sparkline is shown when no timeseries rows are available.'}
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3 font-mono text-[11px] shadow-inner">
                  <span className="text-slate-500 text-[10px] uppercase block font-semibold">Breakout explanation trace</span>
                  <div className="space-y-2">
                    {selectedRepo.explanationTrace.map((item) => (
                      <div key={item} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-700">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

              </div>

              {/* CTA Action in Sidebar Drawer */}
              <div className="pt-6 border-t border-slate-200">
                <button 
                  onClick={() => window.open(selectedRepo.repoUrl, '_blank', 'noopener,noreferrer')}
                  className="w-full px-5 py-3 rounded-lg bg-slate-900 hover:bg-slate-850 text-white font-semibold text-center text-xs flex items-center justify-center gap-1.5 cursor-pointer shadow-md active:scale-95 transition-all"
                >
                  <LineChart className="w-4 h-4" /> Open Repository on GitHub
                </button>
              </div>

            </motion.div>
          </>
        )}
      </AnimatePresence>

    </div>
  );
};
