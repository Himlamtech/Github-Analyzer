import React from 'react';

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BookOpen, MapPin } from 'lucide-react';

import type { WeeklyBriefArchiveEntry, WeeklyBriefSnapshot } from '../types';

interface WeeklyBriefProps {
  data: WeeklyBriefSnapshot | null;
  archive: WeeklyBriefArchiveEntry[];
  isLoading: boolean;
}

function regionTone(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes('stable')) {
    return 'text-emerald-700 bg-emerald-500';
  }
  if (normalized.includes('lag')) {
    return 'text-indigo-700 bg-indigo-500';
  }
  return 'text-amber-700 bg-amber-500';
}

function formatPublishDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

export const WeeklyBrief: React.FC<WeeklyBriefProps> = ({ data, archive, isLoading }) => {
  if (isLoading && !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">
        Loading weekly brief snapshot...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-800 shadow-sm">
        Weekly brief snapshot is currently unavailable.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-20 font-sans">
      <div className="space-y-2 border-b border-slate-200 pb-6">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 font-mono">
          <BookOpen className="h-3.5 w-3.5" />
          <span>Macro Research Division • Published {formatPublishDate(data.publishedAt)}</span>
        </div>
        <h1 className="text-3xl font-display font-medium tracking-tight text-slate-950 sm:text-4xl">
          {data.title}
        </h1>
        <p className="max-w-3xl text-sm text-slate-600">{data.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="space-y-10 lg:col-span-2">
          <section className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">
              Strategic Executive Summary
            </h3>

            <div className="space-y-4">
              {data.pillars.map((pillar) => (
                <div
                  key={pillar.pillarNumber}
                  className="flex items-start gap-4 rounded-xl border border-slate-205 bg-white p-5 shadow-sm transition-all hover:border-slate-350"
                >
                  <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded border border-emerald-150 bg-emerald-50 p-2 text-xl font-display font-bold text-emerald-700">
                    {pillar.pillarNumber}
                  </span>
                  <div className="space-y-1">
                    <h4 className="text-sm font-display font-bold text-slate-950">
                      {pillar.title}
                    </h4>
                    <p className="text-xs leading-relaxed text-slate-600">
                      {pillar.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-mono">
              Attention Rotation metrics: RAG vs Agentic
            </h3>

            <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <h4 className="text-sm font-display font-semibold text-slate-900">
                    Standard RAG vs. Agentic Workflow attention share (%)
                  </h4>
                  <p className="text-[10px] text-slate-500 font-mono">
                    Aggregated GitHub relative repo clones & code lines modified
                  </p>
                </div>

                <div className="flex gap-4 text-[10px] font-mono">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded bg-rose-500" /> Standard RAG
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded bg-emerald-500" /> Agentic Loops
                  </span>
                </div>
              </div>

              <div className="h-48 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.summaryChartData} margin={{ top: 5, right: 5, left: -24, bottom: 5 }}>
                    <XAxis dataKey="period" stroke="#475569" style={{ fontSize: 10, fontFamily: 'monospace' }} />
                    <YAxis stroke="#475569" style={{ fontSize: 10, fontFamily: 'monospace' }} />
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
                    <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderColor: '#cbd5e1', fontSize: 11, color: '#0f172a' }} />
                    <Bar dataKey="standardRAG" name="Standard RAG" fill="#f43f5e" radius={[4, 4, 0, 0]} opacity={0.8} />
                    <Bar dataKey="agenticLoops" name="Agentic Workflows" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        </div>

        <div className="col-span-1 space-y-6">
          <div className="space-y-3 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
            <h3 className="block text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">
              Evidence Spotlight
            </h3>
            <p className="select-none text-xs font-display font-semibold uppercase text-slate-900">
              {data.evidenceSpotlightTitle}
            </p>
            <p className="text-xs leading-relaxed text-slate-600">
              {data.evidenceSpotlightBody}
            </p>
            <div className="pt-2">
              <span className="block w-fit rounded border border-emerald-150 bg-emerald-50 p-1.5 px-2 text-[11px] font-bold text-emerald-700 font-mono">
                {data.evidenceSpotlightBadge}
              </span>
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
            <div className="space-y-1">
              <h3 className="block text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">
                Regional Lag Indicators
              </h3>
              <p className="text-xs font-display font-semibold text-slate-900">
                Geographic active deployments
              </p>
            </div>

            <div className="space-y-3 text-[11px] font-mono">
              {data.regionalIndicators.map((indicator) => {
                const [textTone, barTone] = regionTone(indicator.status).split(' ');

                return (
                  <div key={indicator.region} className="space-y-1.5">
                    <div className="flex justify-between text-[10px]">
                      <span className="flex items-center gap-1 text-slate-700">
                        <MapPin className="h-3.5 w-3.5 text-slate-400" />
                        {indicator.region}
                      </span>
                      <span className={`font-semibold ${textTone}`}>
                        {indicator.status} ({indicator.activePercentage}% active)
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded bg-slate-100">
                      <div
                        className={`h-full ${barTone}`}
                        style={{ width: `${indicator.activePercentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-150 bg-slate-50 p-5">
            <h3 className="block text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">
              Research Core Compiled By
            </h3>

            <div className="space-y-3">
              {data.authors.map((author) => (
                <div key={author.initials} className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-xs font-bold text-slate-700 shadow-sm">
                    {author.initials}
                  </div>
                  <div>
                    <h5 className="text-xs font-display font-bold text-slate-900">
                      {author.name}
                    </h5>
                    <span className="text-[10px] text-slate-500 font-mono">{author.role}</span>
                  </div>
                </div>
              ))}
            </div>

            <p className="border-t border-slate-150 pt-2.5 text-[10px] leading-relaxed text-slate-500 font-mono">
              Disclaimer: {data.disclaimer}
            </p>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
            <div className="space-y-1">
              <h3 className="block text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">
                Archive Timeline
              </h3>
              <p className="text-xs font-display font-semibold text-slate-900">
                Versioned brief history from the backend archive route
              </p>
            </div>

            <div className="space-y-3 text-[11px] font-mono">
              {archive.map((entry) => {
                const isCurrent = entry.briefId === data.briefId;

                return (
                  <div
                    key={entry.briefId}
                    className={`rounded border px-3 py-2 ${
                      isCurrent
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                        : 'border-slate-150 bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <strong className="font-sans text-xs font-bold">{entry.title}</strong>
                      <span>{formatPublishDate(entry.publishedAt)}</span>
                    </div>
                    <p className="mt-1 text-[10px] leading-relaxed opacity-80">{entry.subtitle}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
