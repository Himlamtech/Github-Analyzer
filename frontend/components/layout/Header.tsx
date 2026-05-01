import { Activity, GitBranch, Layers3, Radar, Search } from "lucide-react";

interface Props {
  days: number;
  categoryLabel: string;
  selectedRepo: string | null;
}

const NAV_ITEMS = [
  { href: "#pulse", label: "Pulse", icon: Radar },
  { href: "#movement", label: "Movement", icon: Activity },
  { href: "#ecosystem", label: "Ecosystem", icon: Layers3 },
  { href: "#intelligence", label: "Intelligence", icon: Search },
];

export function Header({ days, categoryLabel, selectedRepo }: Props) {
  return (
    <header className="sticky top-0 z-50 px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-3 rounded-[24px] border border-slate-200/85 bg-white/78 px-4 py-3 shadow-[0_18px_46px_-34px_rgba(15,23,42,0.24)] backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-gradient-to-br from-sky-100 via-white to-cyan-100 shadow-[0_12px_26px_-18px_rgba(14,165,233,0.35)]">
            <GitBranch className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="text-gradient text-lg font-semibold tracking-tight">
              GitHub AI Trend Analyzer
            </div>
            <div className="hidden text-xs text-slate-500 lg:block">
              Real-time market intelligence for breakout repos, category shifts, and AI
              repository narratives
            </div>
          </div>
        </div>

        <nav className="hidden items-center gap-1 rounded-full border border-slate-200 bg-slate-50/85 p-1 lg:flex">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;

            return (
              <a
                key={item.href}
                href={item.href}
                className="flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-white hover:text-slate-900"
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </a>
            );
          })}
        </nav>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="rounded-full border border-slate-200 bg-slate-50/85 px-3 py-1.5 text-xs text-slate-600">
            {days}d window
          </div>
          <div className="hidden rounded-full border border-slate-200 bg-slate-50/85 px-3 py-1.5 text-xs text-slate-600 md:block">
            {categoryLabel}
          </div>
          <div className="hidden max-w-[260px] truncate rounded-full border border-slate-200 bg-slate-50/85 px-3 py-1.5 text-xs text-slate-600 xl:block">
            {selectedRepo ?? "No repo selected"}
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-200/80 bg-white/80 px-3 py-1.5 text-xs text-muted-foreground shadow-[0_14px_30px_-22px_rgba(16,185,129,0.35)]">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <Activity className="h-3 w-3" />
            <span>Live</span>
          </div>
        </div>
      </div>
    </header>
  );
}
