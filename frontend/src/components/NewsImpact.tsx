import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Activity, 
  GitCommit, 
  ArrowRight, 
  Sparkles, 
  LineChart, 
  Info, 
  ArrowRightCircle, 
  CheckCircle,
  HelpCircle,
  ShieldCheck,
  TrendingDown
} from 'lucide-react';
import { ResponsiveContainer, LineChart as ReLineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { NEWS_IMPACT_EVENTS } from '../data';
import { NewsImpactEvent } from '../types';

export const NewsImpact: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState<NewsImpactEvent>(NEWS_IMPACT_EVENTS[0]);

  return (
    <div className="space-y-8 pb-20 font-sans">
      
      {/* Scope Header */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-display font-medium text-slate-950 tracking-tight flex items-center gap-2">
          <Activity className="w-6 h-6 text-amber-600" />
          News-to-Code Impact Tracker
        </h1>
        <p className="text-slate-650 text-sm">
          Connecting market narratives back to bare-metal codebase reality. Observe how press releases trigger live commits hours later.
        </p>
      </div>

      {/* PRIMARY SUITE GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* 1. Left System Causality Sidebar (1 column) */}
        <div className="col-span-1 bg-white border border-slate-205 shadow-sm p-5 rounded-xl space-y-6">
          
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block font-bold">
              Causality Analytics
            </span>
            <h3 className="text-slate-900 text-sm font-semibold font-display">System Status</h3>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-100 rounded-lg space-y-3 font-mono text-xs shadow-inner">
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">STATUS</span>
              <strong className="text-emerald-700 uppercase flex items-center gap-1 font-semibold">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping" />
                Active proxy
              </strong>
            </div>
            
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">CAUSALITY INDEX</span>
              <strong className="text-slate-900 font-bold">88.5 / 100</strong>
            </div>

            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">TIME SHIFT LAG</span>
              <strong className="text-slate-900 font-bold">~4.8 Hours</strong>
            </div>
          </div>

          <div className="space-y-3.5">
            <h4 className="text-slate-800 text-xs font-bold font-sans">Causality Index Scope</h4>
            
            <div className="space-y-2 text-[11px] text-slate-600 leading-relaxed">
              <p>
                Our proprietary <strong>Causality Index</strong> analyzes semantic news weights and tracks immediate commit loops to correlate corporate announcements to GitHub forking spikes.
              </p>
              <p>
                Indices above <strong>80/100</strong> indicate extremely direct product market fit, prompting early code migrations within 24 hours of general announcement release.
              </p>
            </div>
          </div>

          <div className="pt-2.5">
            <div className="p-3 bg-amber-50 border border-amber-150 rounded-lg text-[11px] font-mono text-amber-800 flex items-start gap-2 shadow-sm">
              <Info className="w-4 h-4 flex-shrink-0 text-amber-600" />
              <span>Select any event card on the right to load dynamic code adoption curves.</span>
            </div>
          </div>

        </div>

        {/* 2. Middle Event Timeline (2 columns) */}
        <div className="col-span-1 lg:col-span-2 space-y-4">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block font-bold">
            Chronological Impact Feed
          </span>

          {/* Interactive Timeline list */}
          <div className="space-y-4 relative pl-3.5 border-l border-slate-205">
            {NEWS_IMPACT_EVENTS.map((event) => {
              const liesSelected = selectedEvent.id === event.id;
              
              return (
                <div 
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  className={`bg-white p-5 rounded-xl border transition-all relative group cursor-pointer shadow-sm
                    ${liesSelected 
                      ? 'border-amber-400 bg-white ring-1 ring-amber-400 shadow-md' 
                      : 'border-slate-200 hover:border-slate-350'
                    }`}
                >
                  
                  {/* Timeline bullet tag */}
                  <span className={`absolute -left-[21px] top-6 w-3 h-3 rounded-full border-2 
                    ${liesSelected ? 'bg-amber-500 border-white scale-125' : 'bg-slate-200 border-white group-hover:bg-slate-400'}`} 
                  />

                  {/* Header Row */}
                  <div className="flex flex-wrap items-center justify-between gap-2.5 text-[10px] font-mono text-slate-500">
                    <span className="text-slate-800 font-semibold bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
                      {event.date}
                    </span>
                    <span>Causality Score: <strong className={liesSelected ? 'text-amber-700' : 'text-slate-700 font-bold'}>{event.causalityScore}</strong></span>
                  </div>

                  {/* Headline */}
                  <h4 className="text-slate-900 text-sm font-display font-bold mt-3 group-hover:text-amber-700 transition-colors">
                    {event.headline}
                  </h4>

                  <p className="text-slate-600 text-xs leading-relaxed mt-2 font-normal line-clamp-2">
                    {event.summary}
                  </p>

                  {/* Impact Summary tag banner */}
                  <div className="flex items-center justify-between pt-3 border-t border-slate-100 mt-4 text-[10px] font-mono text-slate-500">
                    <span className="uppercase text-slate-500 font-semibold">{event.category}</span>
                    <span className="text-emerald-700 font-bold bg-emerald-50 border border-emerald-150 px-2 py-0.5 rounded">
                      {event.codeImpactMetric}
                    </span>
                  </div>

                </div>
              );
            })}
          </div>

        </div>

        {/* 3. Right Analytics Visualizer (1 column) */}
        <div className="col-span-1 bg-white border border-slate-200 shadow-sm p-5 rounded-xl flex flex-col justify-between min-h-[360px]">
          
          <div className="space-y-4">
            
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-widest block font-semibold text-slate-500">
                Hourly adoption speed
              </span>
              <h3 className="text-slate-900 text-sm font-semibold font-display">Time-Shift Graph</h3>
            </div>

            {/* Event Name */}
            <h4 className="text-amber-700 font-display font-medium text-xs font-mono uppercase tracking-wide">
              {selectedEvent.category} TELEMETRY
            </h4>

            {/* Recharts Adopt Graph */}
            <div className="h-40 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ReLineChart data={selectedEvent.codeTrendData} margin={{ top: 5, right: 5, left: -24, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
                  <XAxis dataKey="time" stroke="#475569" style={{ fontSize: 9, fontFamily: 'monospace' }} />
                  <YAxis stroke="#475569" style={{ fontSize: 9, fontFamily: 'monospace' }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', fontSize: 10, color: '#0f172a' }}
                    labelStyle={{ color: '#0f172a', fontWeight: 'bold' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#f59e0b" 
                    strokeWidth={2.5} 
                    dot={{ fill: '#d97706', strokeWidth: 1 }} 
                    activeDot={{ r: 5 }} 
                  />
                </ReLineChart>
              </ResponsiveContainer>
            </div>

            {/* Narrative text description */}
            <div className="space-y-1.5 font-mono text-[11px] leading-relaxed select-text">
              <span className="text-slate-500 uppercase block font-bold">Research Narrative</span>
              <p className="text-slate-700 bg-slate-50 border border-slate-100 rounded p-2.5 text-xs text-[11px] leading-relaxed max-h-36 overflow-y-auto">
                {selectedEvent.narrativeText}
              </p>
            </div>

          </div>

          {/* Core Action */}
          <div className="pt-4 border-t border-slate-100 mt-4">
            <button 
              onClick={() => alert(`Redirecting to complete research brief on: ${selectedEvent.headline}`)}
              className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-[11px] rounded flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition-all"
            >
              Request Full Causality Dossier <CheckCircle className="w-3.5 h-3.5 text-emerald-450" />
            </button>
          </div>

        </div>

      </div>

    </div>
  );
};
