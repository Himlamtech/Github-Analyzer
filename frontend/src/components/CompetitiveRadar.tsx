import React, { useEffect, useState } from 'react';

import { CheckCircle, Compass, ShieldAlert } from 'lucide-react';

import type { FrameworkRadarItem, RadarSummaryItem } from '../types';

interface CompetitiveRadarProps {
  items: FrameworkRadarItem[];
  winners: RadarSummaryItem[];
  warnings: RadarSummaryItem[];
  isLoading: boolean;
}

function getCoordinates(radiusValue: number, angleIndex: number, totalPoints: number) {
  const angle = (angleIndex / totalPoints) * 2 * Math.PI - Math.PI / 2;
  const radius = 60 + radiusValue * 100;

  return {
    x: 200 + radius * Math.cos(angle),
    y: 201 + radius * Math.sin(angle),
  };
}

export const CompetitiveRadar: React.FC<CompetitiveRadarProps> = ({
  items,
  winners,
  warnings,
  isLoading,
}) => {
  const [selectedItem, setSelectedItem] = useState<FrameworkRadarItem | null>(items[0] ?? null);

  useEffect(() => {
    if (!items.length) {
      setSelectedItem(null);
      return;
    }

    setSelectedItem((current) => items.find((item) => item.id === current?.id) ?? items[0]);
  }, [items]);

  if (isLoading && items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">
        Loading framework radar snapshot...
      </div>
    );
  }

  if (!selectedItem) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-800 shadow-sm">
        Framework radar snapshot is currently unavailable.
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-20 font-sans">
      <div className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-display font-medium tracking-tight text-slate-950 sm:text-3xl">
          <Compass className="h-6 w-6 text-emerald-600" />
          Competitive Radar: Mapping the Framework Frontier
        </h1>
        <p className="text-sm text-slate-600">
          Tracking the positions of dominant AI orchestration frameworks on concentric axes
          measuring velocity and readiness.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="relative flex min-h-[440px] flex-col justify-between overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-5">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-emerald-600 font-mono">
                Spatial Coordinate Map
              </span>
              <h3 className="text-sm font-display font-semibold text-slate-900">
                Concentric Framework Frontier
              </h3>
            </div>

            <div className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-500 shadow-inner font-mono">
              Center = Outbreak Zone (Fastest)
            </div>
          </div>

          <div className="relative flex flex-1 items-center justify-center py-6">
            <svg
              viewBox="0 0 400 400"
              className="h-[300px] w-[300px] select-none sm:h-[320px] sm:w-[320px]"
            >
              <circle cx="200" cy="200" r="45" fill="none" stroke="#10b981" strokeWidth="1" strokeDasharray="2,2" opacity={0.6} />
              <text x="200" y="145" textAnchor="middle" fill="#047857" className="text-[7px] font-semibold font-mono" opacity={0.6}>
                OUTBREAK CENTER
              </text>
              <circle cx="200" cy="200" r="95" fill="none" stroke="#94a3b8" strokeWidth="1" opacity={0.7} />
              <text x="200" y="95" textAnchor="middle" fill="#475569" className="text-[7px] font-semibold font-mono" opacity={0.6}>
                VELOCITY ZIP
              </text>
              <circle cx="200" cy="200" r="145" fill="none" stroke="#cbd5e1" strokeWidth="1.5" opacity={0.8} />
              <text x="200" y="47" textAnchor="middle" fill="#64748b" className="text-[7px] font-semibold font-mono" opacity={0.6}>
                DOMINATIVE TIER
              </text>
              <line x1="200" y1="55" x2="200" y2="345" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3,3" opacity={0.6} />
              <line x1="55" y1="200" x2="345" y2="200" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3,3" opacity={0.6} />
              <text x="345" y="196" textAnchor="end" fill="#64748b" className="text-[7px] font-semibold uppercase font-mono">
                Readiness Zone
              </text>
              <text x="200" y="340" textAnchor="middle" fill="#64748b" className="text-[7px] font-semibold uppercase font-mono">
                Deploy Readiness
              </text>

              {items.map((item, index) => {
                const coords = getCoordinates(item.developerVelocity, index, items.length);
                const isSelected = selectedItem.id === item.id;
                const isBreakout = item.id === 'crewai';

                return (
                  <g
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className="cursor-pointer group"
                  >
                    <circle
                      cx={coords.x}
                      cy={coords.y}
                      r={isSelected ? 10 : 6}
                      fill={
                        isBreakout
                          ? 'rgba(16,185,129,0.1)'
                          : isSelected
                            ? 'rgba(99,102,241,0.1)'
                            : 'transparent'
                      }
                      className="transition-all duration-300"
                    />
                    <circle
                      cx={coords.x}
                      cy={coords.y}
                      r={isSelected ? 5 : 4}
                      className={`stroke-2 transition-all duration-300 ${
                        isBreakout
                          ? 'fill-emerald-500 stroke-emerald-400'
                          : isSelected
                            ? 'fill-indigo-650 stroke-indigo-400'
                            : 'fill-white stroke-slate-400 hover:fill-slate-100'
                      }`}
                    />
                    <text
                      x={coords.x + 8}
                      y={coords.y + 3}
                      fill={isSelected ? '#4338ca' : '#475569'}
                      className="text-[9px] font-bold font-mono"
                    >
                      {item.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="rounded-lg border border-slate-150 bg-slate-50 p-3 text-xs text-slate-500 shadow-inner font-mono">
            Concentric coordinate axes represent inverse developer frequency. Proximity to
            center represents rapid breakout velocity.
          </div>
        </div>

        <div className="flex flex-col justify-between gap-6 lg:col-span-4">
          <div className="flex flex-1 flex-col justify-between space-y-6 rounded-xl border border-slate-205 bg-white p-6 shadow-sm">
            <div className="space-y-4">
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 font-mono">
                  Intelligence Dossier
                </span>
                <h3 className="text-lg font-display font-bold text-slate-900">
                  {selectedItem.name} Trajectory
                </h3>
              </div>

              <div className="space-y-3.5 pt-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500 font-mono">
                  Contributor density energy
                </span>

                <div className="space-y-1 text-[11px] font-mono">
                  <div className="flex justify-between text-slate-500">
                    <span>INDEX RATING</span>
                    <strong className="font-bold text-emerald-700">
                      {selectedItem.contributorEnergy}%
                    </strong>
                  </div>
                  <div className="h-2 w-full rounded border border-slate-150 bg-slate-100">
                    <div
                      className="h-full rounded bg-emerald-500 transition-all duration-500"
                      style={{ width: `${selectedItem.contributorEnergy}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <span className="block text-[10px] font-bold uppercase text-slate-500 font-mono">
                  Strategic Research Insight
                </span>
                <p className="rounded-lg border border-slate-100 bg-slate-50 p-3.5 text-xs leading-relaxed text-slate-700">
                  {selectedItem.strategicInsight}
                </p>
              </div>
            </div>

            <div className="space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-600 font-mono">
              <div className="flex justify-between border-b border-slate-100 py-1">
                <span className="text-slate-500">Sector classification</span>
                <strong className="font-bold text-slate-900">Orchestration Framework</strong>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Market deployment footprint</span>
                <strong className="font-bold text-slate-900">
                  {selectedItem.marketFootprint}
                </strong>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-6 lg:col-span-3">
          <div className="space-y-4 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
            <h3 className="text-xs font-bold uppercase tracking-widest text-emerald-700 font-mono">
              Frontier Winners
            </h3>

            <div className="space-y-3 text-[11px] font-mono">
              {winners.map((winner) => (
                <div
                  key={winner.title}
                  className="flex items-center gap-2 rounded border border-slate-150 bg-slate-50 p-2"
                >
                  <CheckCircle className="h-4 w-4 flex-shrink-0 text-emerald-600" />
                  <div>
                    <strong className="block font-sans font-bold text-slate-900">
                      {winner.title}
                    </strong>
                    <span className="text-slate-500">{winner.summary}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-205 bg-white p-5 shadow-sm">
            <h3 className="text-xs font-bold uppercase tracking-widest text-rose-700 font-mono">
              Attrition Warnings
            </h3>

            <div className="space-y-3 text-[11px] font-mono">
              {warnings.map((warning) => (
                <div
                  key={warning.title}
                  className="flex items-center gap-2 rounded border border-slate-150 bg-slate-50 p-2"
                >
                  <ShieldAlert className="h-4 w-4 flex-shrink-0 text-rose-500" />
                  <div>
                    <strong className="block font-sans font-bold text-slate-900">
                      {warning.title}
                    </strong>
                    <span className="text-slate-500">{warning.summary}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
