import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Activity,
  Bell,
  Clock,
  Command,
  Compass,
  Layers,
  Menu,
  Radio,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react';

import { useDashboardData } from './hooks/useDashboardData';
import { useBreakoutData } from './hooks/useBreakoutData';
import { useFrameworkRadarData } from './hooks/useFrameworkRadarData';
import { useNewsImpactData } from './hooks/useNewsImpactData';
import { useRotationData } from './hooks/useRotationData';
import { API_BASE_URL } from './lib/api';
import { BreakoutDetector } from './components/BreakoutDetector';
import { CompetitiveRadar } from './components/CompetitiveRadar';
import { EcosystemRotation } from './components/EcosystemRotation';
import { NewsImpact } from './components/NewsImpact';
import { Overview } from './components/Overview';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [customToast, setCustomToast] = useState<string | null>(null);
  const { data, isLoading, error } = useDashboardData();
  const {
    repositories: breakoutRepositories,
    isLoading: isBreakoutLoading,
    error: breakoutError,
  } = useBreakoutData();
  const {
    data: frameworkRadar,
    isLoading: isFrameworkRadarLoading,
    error: frameworkRadarError,
  } = useFrameworkRadarData(activeTab === 'radar');
  const {
    events: newsImpactEvents,
    readiness: newsImpactReadiness,
    isLoading: isNewsImpactLoading,
    error: newsImpactError,
  } = useNewsImpactData(activeTab === 'newsImpact');
  const {
    categories: rotationCategories,
    isLoading: isRotationLoading,
    error: rotationError,
  } = useRotationData(activeTab === 'overview' || activeTab === 'ecosystems');

  useEffect(() => {
    window.alert = (message: string) => {
      setCustomToast(message);
    };
  }, []);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toUTCString().replace('GMT', 'UTC'));
    };

    updateTime();
    const interval = window.setInterval(updateTime, 1000);
    return () => window.clearInterval(interval);
  }, []);

  const navigationTabs = useMemo(
    () => [
      { id: 'overview', label: 'Overview', icon: Radio },
      { id: 'breakout', label: 'Breakout screener', icon: TrendingUp },
      { id: 'ecosystems', label: 'Ecosystem shifts', icon: Layers },
      { id: 'newsImpact', label: 'News Impact', icon: Activity },
      { id: 'radar', label: 'Framework Radar', icon: Compass },
    ],
    [],
  );

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const pipelineStateLabel = data?.pipelineStatus?.status ?? (isLoading ? 'loading' : 'offline');
  const topRepoName = data?.trendingRepos[0]?.fullName ?? 'Awaiting live data';
  const topRepoVelocity = data?.trendingRepos[0]?.velocityChange ?? '--';
  const latestEvent = data?.latestEvents[0];
  const activeSurfaceError =
    activeTab === 'overview'
      ? error
      : activeTab === 'breakout'
        ? breakoutError
        : activeTab === 'ecosystems'
          ? rotationError
          : activeTab === 'newsImpact'
            ? newsImpactError
            : activeTab === 'radar'
              ? frameworkRadarError
              : null;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col selection:bg-emerald-100 selection:text-emerald-950 font-sans">
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex justify-between items-center text-[10px] font-mono tracking-wider text-slate-500">
        <div className="flex items-center gap-6 overflow-hidden max-w-[70%] sm:max-w-none">
          <div className="flex items-center gap-1.5 text-emerald-600 font-bold select-none">
            <span className={`w-1.5 h-1.5 rounded-full ${pipelineStateLabel === 'healthy' ? 'bg-emerald-500 animate-ping' : 'bg-amber-500'}`} />
            <span>{pipelineStateLabel === 'healthy' ? 'PIPELINE ONLINE' : pipelineStateLabel.toUpperCase()}</span>
          </div>

          <div className="hidden md:block overflow-hidden relative w-[34rem] h-4">
            <div className="absolute whitespace-nowrap animate-[marquee_25s_linear_infinite] hover:pause">
              &gt;&gt; live API source: <span className="text-emerald-600 font-semibold">{API_BASE_URL}</span>
              {' '}• trending repo: <span className="text-emerald-600 font-semibold">{topRepoName}</span>
              {' '}({topRepoVelocity})
              {' '}• latest event: <span className="text-emerald-600 font-semibold">{latestEvent?.eventType ?? 'waiting'}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 select-none">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{currentTime || 'Loading UTC...'}</span>
        </div>
      </div>

      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 py-4 sm:px-6 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div onClick={() => handleTabChange('overview')} className="flex items-center gap-2.5 cursor-pointer group">
            <div className="p-2 bg-gradient-to-br from-emerald-50 to-teal-50/5 border border-emerald-200 rounded-lg text-emerald-600 group-hover:border-emerald-300 group-hover:shadow-[0_0_15px_rgba(16,185,129,0.1)] transition-all">
              <Command className="w-5 h-5 animate-pulse" />
            </div>
            <div className="space-y-0.5">
              <span className="font-display font-bold text-lg text-slate-900 leading-none tracking-tight block">
                STRATEGA
              </span>
              <span className="text-[9px] font-mono tracking-widest text-slate-400 block uppercase">
                GitHub Signal Intelligence
              </span>
            </div>
          </div>

          <nav className="hidden lg:flex items-center gap-1 font-mono">
            {navigationTabs.map((tab) => {
              const IconComp = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-2 group border border-transparent ${
                    isActive
                      ? 'bg-slate-900 border-slate-800 text-white font-bold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <IconComp className={`w-3.5 h-3.5 transition-colors ${isActive ? 'text-emerald-500' : 'text-slate-400 group-hover:text-slate-600'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const status = data?.pipelineStatus;
                const message = status
                  ? `Pipeline status: ${status.status}. ClickHouse reachable: ${status.clickhouseReachable}. Parquet path ready: ${status.parquetPathExists}.`
                  : error ?? 'Dashboard data is still loading.';
                alert(message);
              }}
              className="p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 text-slate-500 hover:text-slate-800 transition-all relative cursor-pointer"
              id="header-notification-bell"
            >
              <Bell className="w-4 h-4" />
              <span className={`absolute top-1 right-1 w-2 h-2 rounded-full ${error ? 'bg-amber-500' : 'bg-emerald-500'} ${!error ? 'animate-ping' : ''}`} />
            </button>

            <button
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="p-2 rounded-lg bg-white border border-slate-200 text-slate-500 hover:text-slate-800 lg:hidden cursor-pointer"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden border-b border-slate-200 bg-white px-4 py-4 space-y-2 relative z-30 shadow-md"
          >
            {navigationTabs.map((tab) => {
              const IconComp = tab.icon;
              const isActive = activeTab === tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`w-full px-4 py-3 rounded-lg text-xs font-mono text-left cursor-pointer flex items-center gap-3 transition-colors ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <IconComp className={`w-4 h-4 ${isActive ? 'text-emerald-500' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8">
        {activeSurfaceError && (
          <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Live dashboard data is temporarily unavailable for this surface. The app will retry automatically. Error: {activeSurfaceError}
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
          >
            {activeTab === 'overview' && (
              <Overview
                data={data}
                isLoading={isLoading}
                onNavigate={handleTabChange}
              />
            )}
            {activeTab === 'breakout' && (
              <BreakoutDetector
                isLoading={isBreakoutLoading}
                repositories={breakoutRepositories}
              />
            )}
            {activeTab === 'ecosystems' && (
              <EcosystemRotation
                categories={rotationCategories}
                isLoading={isRotationLoading}
                error={rotationError}
              />
            )}
            {activeTab === 'newsImpact' && (
              <NewsImpact
                events={newsImpactEvents}
                readiness={newsImpactReadiness}
                isLoading={isNewsImpactLoading}
              />
            )}
            {activeTab === 'radar' && (
              <CompetitiveRadar
                items={frameworkRadar?.frameworks ?? []}
                winners={frameworkRadar?.winners ?? []}
                warnings={frameworkRadar?.warnings ?? []}
                isLoading={isFrameworkRadarLoading}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {customToast && (
          <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full">
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              className="bg-white border border-emerald-200 p-5 rounded-2xl shadow-2xl flex items-start gap-3.5 backdrop-blur-md"
            >
              <div className="p-2 bg-emerald-50 border border-emerald-100 text-emerald-600 rounded-lg flex-shrink-0 animate-pulse">
                <Sparkles className="w-5 h-5" />
              </div>
              <div className="space-y-1 relative flex-1">
                <div className="text-slate-900 text-xs font-bold font-display uppercase tracking-wider block">
                  Stratega Notice
                </div>
                <p className="text-slate-600 text-xs leading-relaxed max-h-36 overflow-y-auto select-text">
                  {customToast}
                </p>
                <button
                  onClick={() => setCustomToast(null)}
                  className="absolute -top-1 -right-1 text-slate-400 hover:text-slate-800 font-mono text-[10px] p-1 font-bold cursor-pointer"
                >
                  DISMISS
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <footer className="bg-white border-t border-slate-200 py-12 px-4 text-center mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6 opacity-80 hover:opacity-100 transition-opacity font-mono text-xs text-slate-500">
          <div className="flex items-center gap-2 font-display text-slate-800 text-sm font-semibold">
            <Command className="w-4 h-4 text-emerald-500" />
            <span>STRATEGA GITHUB ANALYZER</span>
          </div>

          <div className="flex gap-4">
            <span className="hover:text-slate-800 cursor-pointer">Live Dashboard</span>
            <span>•</span>
            <span className="hover:text-slate-800 cursor-pointer">FastAPI Analytics</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
