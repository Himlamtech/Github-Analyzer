import React, { useEffect, useMemo, useState } from 'react';

import { Activity, CheckCircle, Info } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart as ReLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { NewsImpactEvent } from '../types';

interface NewsImpactProps {
  events: NewsImpactEvent[];
  isLoading: boolean;
}

export const NewsImpact: React.FC<NewsImpactProps> = ({ events, isLoading }) => {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(events[0]?.id ?? null);

  useEffect(() => {
    if (!events.length) {
      setSelectedEventId(null);
      return;
    }

    setSelectedEventId((current) => events.find((event) => event.id === current)?.id ?? events[0].id);
  }, [events]);

  const selectedEvent = useMemo(
    () => events.find((event) => event.id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const averageCausality = useMemo(() => {
    if (!events.length) {
      return 0;
    }
    return Number((events.reduce((sum, event) => sum + event.causalityScore, 0) / events.length).toFixed(1));
  }, [events]);

  const averageLag = useMemo(() => {
    if (!events.length) {
      return 0;
    }
    const totalLag = events.reduce((sum, event) => {
      const numericLag = Number.parseFloat(event.timeOffset);
      return sum + (Number.isNaN(numericLag) ? 0 : numericLag);
    }, 0);
    return Number((totalLag / events.length).toFixed(1));
  }, [events]);

  if (isLoading && events.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">
        Loading news impact snapshot...
      </div>
    );
  }

  if (!selectedEvent) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-800 shadow-sm">
        News impact snapshot is currently unavailable.
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-20 font-sans">
      <div className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-display font-medium tracking-tight text-slate-950 sm:text-3xl">
          <Activity className="h-6 w-6 text-amber-600" />
          News-to-Code Impact Tracker
        </h1>
        <p className="text-sm text-slate-600">
          Connecting market narratives back to bare-metal codebase reality. This surface is
          now served from a curated backend snapshot while the external-source ingestion layer
          is being built.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="col-span-1 space-y-6 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
          <div className="space-y-1">
            <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-500 font-mono">
              Causality Analytics
            </span>
            <h3 className="text-sm font-display font-semibold text-slate-900">System Status</h3>
          </div>

          <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs shadow-inner font-mono">
            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">STATUS</span>
              <strong className="flex items-center gap-1 font-semibold uppercase text-amber-700">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                Hybrid live snapshot
              </strong>
            </div>

            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">CAUSALITY INDEX</span>
              <strong className="font-bold text-slate-900">{averageCausality} / 100</strong>
            </div>

            <div className="flex justify-between border-b border-slate-200 pb-2">
              <span className="text-slate-500">TIME SHIFT LAG</span>
              <strong className="font-bold text-slate-900">~{averageLag} Hours</strong>
            </div>
          </div>

          <div className="space-y-3.5">
            <h4 className="text-xs font-bold text-slate-800">Causality Index Scope</h4>

            <div className="space-y-2 text-[11px] leading-relaxed text-slate-600">
              <p>
                This page now reads a backend-defined intelligence contract backed by persisted
                official-source ingestion and server-computed lag curves.
              </p>
              <p>
                When GitHub telemetry matching is temporarily degraded, the page still serves the
                official event stream and explains the degraded evidence path explicitly.
              </p>
            </div>
          </div>

          <div className="pt-2.5">
            <div className="flex items-start gap-2 rounded-lg border border-amber-150 bg-amber-50 p-3 text-[11px] text-amber-800 shadow-sm font-mono">
              <Info className="h-4 w-4 flex-shrink-0 text-amber-600" />
              <span>Select any event card on the right to load backend-served adoption curves.</span>
            </div>
          </div>
        </div>

        <div className="col-span-1 space-y-4 lg:col-span-2">
          <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-500 font-mono">
            Chronological Impact Feed
          </span>

          <div className="relative space-y-4 border-l border-slate-205 pl-3.5">
            {events.map((event) => {
              const isSelected = selectedEvent.id === event.id;

              return (
                <div
                  key={event.id}
                  onClick={() => setSelectedEventId(event.id)}
                  className={`group relative cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition-all ${
                    isSelected
                      ? 'border-amber-400 ring-1 ring-amber-400 shadow-md'
                      : 'border-slate-200 hover:border-slate-350'
                  }`}
                >
                  <span
                    className={`absolute -left-[21px] top-6 h-3 w-3 rounded-full border-2 ${
                      isSelected
                        ? 'scale-125 border-white bg-amber-500'
                        : 'border-white bg-slate-200 group-hover:bg-slate-400'
                    }`}
                  />

                  <div className="flex flex-wrap items-center justify-between gap-2.5 text-[10px] text-slate-500 font-mono">
                    <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 font-semibold text-slate-800">
                      {event.date}
                    </span>
                    <span>
                      Causality Score:{' '}
                      <strong className={isSelected ? 'text-amber-700' : 'font-bold text-slate-700'}>
                        {event.causalityScore}
                      </strong>
                    </span>
                  </div>

                  <h4 className="mt-3 text-sm font-display font-bold text-slate-900 transition-colors group-hover:text-amber-700">
                    {event.headline}
                  </h4>

                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-600">
                    {event.summary}
                  </p>

                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[10px] text-slate-500 font-mono">
                    <span className="font-semibold uppercase text-slate-500">{event.category}</span>
                    <span className="rounded border border-emerald-150 bg-emerald-50 px-2 py-0.5 font-bold text-emerald-700">
                      {event.codeImpactMetric}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="col-span-1 flex min-h-[360px] flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="space-y-4">
            <div className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-widest text-slate-500 font-mono">
                Hourly adoption speed
              </span>
              <h3 className="text-sm font-display font-semibold text-slate-900">Time-Shift Graph</h3>
            </div>

            <h4 className="text-xs font-display font-medium uppercase tracking-wide text-amber-700 font-mono">
              {selectedEvent.category} TELEMETRY
            </h4>

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

            <div className="space-y-1.5 select-text text-[11px] leading-relaxed font-mono">
              <span className="block font-bold uppercase text-slate-500">Research Narrative</span>
              <p className="max-h-36 overflow-y-auto rounded border border-slate-100 bg-slate-50 p-2.5 text-xs leading-relaxed text-slate-700">
                {selectedEvent.narrativeText}
              </p>
            </div>

            <div className="space-y-1.5 text-[11px] font-mono">
              <span className="block font-bold uppercase text-slate-500">Linked Entities</span>
              <div className="flex flex-wrap gap-2">
                {selectedEvent.linkedEntities.map((entity) => (
                  <span key={entity} className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-slate-700">
                    {entity}
                  </span>
                ))}
              </div>
            </div>

            <div className="space-y-1.5 text-[11px] font-mono">
              <span className="block font-bold uppercase text-slate-500">Top Impacted Repos</span>
              <div className="space-y-2">
                {selectedEvent.topImpactedRepos.map((repo) => (
                  <div key={repo} className="rounded border border-slate-150 bg-slate-50 px-3 py-2 text-slate-700">
                    {repo}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4 border-t border-slate-100 pt-4">
            <button
              onClick={() => alert(`Backend-backed curated dossier ready for: ${selectedEvent.headline}`)}
              className="flex w-full items-center justify-center gap-1.5 rounded bg-slate-900 py-2 text-[11px] font-semibold text-white transition-all hover:bg-slate-800 active:scale-95"
            >
              Request Full Causality Dossier <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
