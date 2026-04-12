import { GitBranch, Activity } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-screen-2xl items-center justify-between rounded-[24px] border border-sky-200/80 bg-white/72 px-4 py-3 shadow-[0_18px_46px_-34px_rgba(37,99,235,0.35)] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-sky-200/80 bg-gradient-to-br from-sky-100 via-white to-cyan-100 shadow-[0_12px_26px_-18px_rgba(14,165,233,0.45)]">
            <GitBranch className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="text-gradient text-lg font-semibold tracking-tight">
              GitHub AI Trends
            </div>
            <div className="hidden text-xs text-slate-500 sm:block">
              Market intelligence for breakout repos, headlines, and momentum shifts
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-emerald-200/80 bg-white/80 px-3 py-1.5 text-xs text-muted-foreground shadow-[0_14px_30px_-22px_rgba(16,185,129,0.45)]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <Activity className="h-3 w-3" />
          <span>Live</span>
        </div>
      </div>
    </header>
  );
}
