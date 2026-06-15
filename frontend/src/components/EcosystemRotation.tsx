import React, { useState } from 'react';
import { motion } from 'motion/react';
import { 
  Layers, 
  ArrowRight, 
  Info, 
  HelpCircle, 
  TrendingUp, 
  Sparkles, 
  Activity, 
  ShieldAlert, 
  Zap 
} from 'lucide-react';

import type { EcosystemCategory } from '../types';

interface EcosystemRotationProps {
  categories: EcosystemCategory[];
  isLoading: boolean;
  error: string | null;
}

export const EcosystemRotation: React.FC<EcosystemRotationProps> = ({
  categories,
  isLoading,
  error,
}) => {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const leadingCategory = categories[0] ?? null;

  if (isLoading && categories.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">
        Loading ecosystem rotation snapshot...
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-800 shadow-sm">
        Ecosystem rotation is currently unavailable{error ? `: ${error}` : '.'}
      </div>
    );
  }

  // SVG Nodes coordinates and metadata for Attention Flow Map
  const NODES = [
    { id: 'n1', label: 'Raw Model APIs', x: 80, y: 150, change: '-4%', attention: 'High', desc: 'Direct completion queries without orchestration' },
    { id: 'n2', label: 'Vector Stores', x: 220, y: 100, change: '+12%', attention: 'Stable', desc: 'Semantic retrieval & embeddings caching' },
    { id: 'n3', label: 'RAG Pipelines', x: 220, y: 220, change: '-24%', attention: 'Down', desc: 'Standard single-query Retrieval-Augmented Generation' },
    { id: 'n4', label: 'Agentic Frameworks', x: 420, y: 160, change: '+144%', attention: 'Extreme', desc: 'Multi-turn autonomous task workflows' },
    { id: 'n5', label: 'State Orchestrations', x: 580, y: 160, change: '+340%', attention: 'Breakout', desc: 'Persistent thread control & execution states' }
  ];

  return (
    <div className="space-y-8 pb-20 font-sans">
      
      {/* Title Header */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-display font-medium text-slate-950 tracking-tight flex items-center gap-2">
          <Layers className="w-6 h-6 text-indigo-500" />
          AI Ecosystem Rotation: Tracking the Shift of Attention
        </h1>
        <p className="text-slate-600 text-sm">
          Quantifying developer migration patterns as workflows evolve from search retrieval into continuous model execution.
        </p>
      </div>

      {/* TWO COLUMN GRID: ACTIVE MAP + STATS SIDEBAR */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Interactive SVG Flow-Map (3 columns) */}
        <div className="col-span-1 lg:col-span-3 bg-white border border-slate-200 shadow-sm p-6 rounded-xl space-y-6 relative overflow-hidden flex flex-col justify-between min-h-[480px]">
          
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-indigo-600 uppercase block tracking-wider font-bold">
                Telemetry Interactive Canvas
              </span>
              <h3 className="text-slate-900 text-sm font-semibold font-display">Attention Flow Map</h3>
            </div>
            
            {/* Help Indicator */}
            <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
              <Info className="w-3.5 h-3.5 text-slate-400" />
              <span>Hover nodes to trace momentum parameters</span>
            </div>
          </div>

          {/* SVG Map Layout with animated nodes */}
          <div className="relative flex-1 min-h-[300px] border border-slate-200 bg-slate-50/50 rounded-lg p-2.5 flex items-center justify-center">
            <svg viewBox="0 0 660 300" className="w-full h-full max-h-[320px]">
              
              {/* Connector lines matching flow structure */}
              <defs>
                <linearGradient id="flowGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#4338ca" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#059669" stopOpacity="0.8" />
                </linearGradient>
                <linearGradient id="flowDropGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#4338ca" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#dc2626" stopOpacity="0.2" />
                </linearGradient>
              </defs>

              {/* Ingress Paths */}
              {/* Node 1 to Node 2 */}
              <path d="M 80,150 L 220,100" fill="none" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3,3" />
              {/* Node 1 to Node 3 */}
              <path d="M 80,150 L 220,220" fill="none" stroke="#94a3b8" strokeWidth="1.5" />
              
              {/* Core Flow Pathways (Node 2 to 4) */}
              <path d="M 220,100 L 420,160" fill="none" stroke="url(#flowGrad1)" strokeWidth="3" />
              {/* Down flow pathway (Node 3 to 4) */}
              <path d="M 220,220 L 420,160" fill="none" stroke="url(#flowDropGrad)" strokeWidth="1.5" />
              
              {/* Breakout Pathway (Node 4 to 5) */}
              <path d="M 420,160 L 580,160" fill="none" stroke="#10b981" strokeWidth="4" />

              {/* Animated dots running across paths */}
              <circle r="3" fill="#10b981">
                <animateMotion dur="4s" repeatCount="indefinite" path="M 220,100 L 420,160" />
              </circle>
              <circle r="2.5" fill="#10b981">
                <animateMotion dur="1.8s" repeatCount="indefinite" path="M 420,160 L 580,160" />
              </circle>
              <circle r="2" fill="#ef4444">
                <animateMotion dur="5s" repeatCount="indefinite" path="M 80,150 L 220,220" />
              </circle>

              {/* Render interactive nodes bubbles */}
              {NODES.map((node) => {
                const isHovered = hoveredNode === node.id;
                const isBreakout = node.change.startsWith('+340') || node.change.startsWith('+144');
                const isDown = node.change.startsWith('-');
                
                return (
                  <g 
                    key={node.id}
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    className="cursor-pointer group"
                  >
                    <circle 
                       cx={node.x} 
                       cy={node.y} 
                       r={isHovered ? 24 : 18} 
                       className={`transition-all duration-300 stroke-2
                        ${isBreakout 
                          ? 'fill-emerald-500/15 stroke-emerald-500 group-hover:fill-emerald-500/25' 
                          : isDown
                            ? 'fill-rose-500/10 stroke-rose-500/40 group-hover:fill-rose-500/20'
                            : 'fill-white stroke-indigo-500/60 group-hover:fill-indigo-50/50'
                        }`} 
                     />
                    
                    {/* Ring glow for Breakout Node */}
                    {isBreakout && (
                      <circle 
                        cx={node.x} 
                        cy={node.y} 
                        r={26} 
                        fill="none" 
                        stroke="#10b981" 
                        strokeWidth="1" 
                        className="animate-ping opacity-30" 
                      />
                    )}

                    {/* Node text tags */}
                    <text 
                      x={node.x} 
                      y={node.y + (isHovered ? 38 : 32)} 
                      textAnchor="middle" 
                      fill={isHovered ? '#1e1b4b' : '#475569'} 
                      className="text-[10px] font-mono select-none font-semibold"
                    >
                      {node.label}
                    </text>

                    {/* Percentage text within bubble */}
                    <text 
                      x={node.x} 
                      y={node.y + 3} 
                      textAnchor="middle" 
                      fill={isBreakout ? '#047857' : isHovered ? '#4338ca' : '#475569'} 
                      className="text-[9px] font-bold font-mono select-none"
                    >
                      {node.change}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Rotation Catalyst Dynamic Tooltip overlays */}
            <div className="absolute bottom-4 left-4 right-4 bg-slate-900 border border-slate-800 p-3.5 rounded-lg flex items-start gap-3 backdrop-blur-sm shadow-lg">
              <Zap className="w-5 h-5 text-indigo-400 flex-shrink-0 animate-bounce mt-0.5" />
              <div className="space-y-0.5 font-mono">
                <span className="text-[10px] uppercase text-indigo-400 font-bold">
                  Rotation Catalyst
                </span>
                <p className="text-slate-300 text-xs text-[11px] leading-relaxed">
                  {hoveredNode 
                    ? `${NODES.find(n => n.id === hoveredNode)?.label}: ${NODES.find(n => n.id === hoveredNode)?.desc}`
                    : leadingCategory?.rotationDrivers?.[0]
                      ?? 'Live ecosystem rotation evidence is waiting for the next telemetry refresh.'
                  }
                </p>
              </div>
            </div>

          </div>

        </div>

        {/* Right Stats Sidebar (1 column) */}
        <div className="col-span-1 flex flex-col gap-6">
          
          {/* Why the Shift? Section */}
          <div className="bg-white border border-slate-200 p-5 rounded-xl space-y-3 shadow-sm">
            <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest block font-bold">
              Market Catalyst
            </h3>
            <p className="text-slate-900 text-sm font-semibold font-display">Why the Shift?</p>
            <p className="text-slate-655 text-slate-600 text-xs leading-relaxed font-normal">
              {leadingCategory?.rotationDrivers?.[1]
                ?? 'The current lead category will expose its top backend evidence here once the latest snapshot is available.'}
            </p>
          </div>

          {/* Category Gaps with visual priorities labels */}
          <div className="bg-white border border-slate-200 p-5 rounded-xl space-y-4 shadow-sm">
            <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest block font-bold">
              Market Opportunity
            </h3>
            <p className="text-slate-900 text-sm font-semibold font-display">Category structural Gaps</p>
            
            <div className="space-y-3 font-mono text-[11px]">
              {/* Gap 1 */}
              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 block text-xs">Evaluators & Testing</span>
                  <span className="text-rose-600 font-semibold text-[10px]">High Friction</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-rose-50 border border-rose-150 text-rose-700 text-[9px] uppercase tracking-wider font-semibold">
                  Critical Gap
                </span>
              </div>

              {/* Gap 2 */}
              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 block text-xs font-sans">Acoustic WebRTC Layer</span>
                  <span className="text-amber-600 font-semibold text-[10px]">Model-Native Voice</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-amber-50 border border-amber-150 text-amber-700 text-[9px] uppercase tracking-wider font-semibold">
                  Strategic
                </span>
              </div>

              {/* Gap 3 */}
              <div className="p-2.5 bg-slate-50 border border-slate-100 rounded flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 block text-xs font-sans">Local Vector Caching</span>
                  <span className="text-indigo-600 font-semibold text-[10px]">Lite memory systems</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-indigo-50 border border-indigo-150 text-indigo-700 text-[9px] uppercase tracking-wider font-semibold">
                  High Value
                </span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* CATEGORY MOMENTUM BENTO CARDS AT BOTTOM */}
      <div className="space-y-4 pt-4">
        <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest block font-bold">
          Telemetry Sector Breakdown
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {categories.map((cat, idx) => {
            const hoverBorder = idx === 0 
              ? 'hover:border-emerald-500/50' 
              : idx === 1 
                ? 'hover:border-indigo-400' 
                : 'hover:border-slate-400';
            
            return (
              <div 
                key={cat.id}
                className={`bg-white border border-slate-200 p-5 rounded-xl flex flex-col justify-between transition-all group shadow-sm ${hoverBorder}`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">
                      Sector Momentum Tracker
                    </span>
                    <span className="text-xs font-mono text-emerald-700 font-semibold bg-emerald-50 border border-emerald-150 px-2 py-0.5 rounded-full">
                      {cat.growth}
                    </span>
                  </div>
                  
                  <h4 className="text-slate-900 text-lg font-display font-semibold group-hover:text-emerald-700 transition-colors">
                    {cat.title}
                  </h4>
                  <p className="text-slate-600 text-xs leading-relaxed font-normal">
                    {cat.description}
                  </p>
                  {cat.topRepos && cat.topRepos.length > 0 && (
                    <p className="text-slate-500 text-[11px] leading-relaxed font-mono">
                      Top repos: {cat.topRepos.join(', ')}
                    </p>
                  )}
                </div>

                {/* Growth scale status */}
                <div className="pt-6 border-t border-slate-100 mt-4 space-y-2 font-mono text-[11px]">
                  <div className="flex justify-between text-slate-505 text-slate-500">
                    <span>INDEX VALUE SCORE</span>
                    <strong className="text-slate-900">{cat.score} / 10</strong>
                  </div>
                  {typeof cat.confidenceScore === 'number' && (
                    <div className="flex justify-between text-slate-505 text-slate-500">
                      <span>CONFIDENCE</span>
                      <strong className="text-slate-900">{cat.confidenceScore.toFixed(1)} / 100</strong>
                    </div>
                  )}
                  <div className="w-full h-1.5 bg-slate-50 border border-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                      style={{ width: `${cat.momentum}%` }}
                    />
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
};
