import { GitBranch, Sparkles } from "lucide-react";

export function Footer() {
  return (
    <footer className="px-4 pb-6 pt-2 sm:px-6">
      <div className="mx-auto flex max-w-screen-2xl flex-col gap-4 rounded-[28px] border border-slate-200/85 bg-white/78 px-5 py-5 shadow-[0_18px_46px_-34px_rgba(15,23,42,0.18)] backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
            <GitBranch className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-950">
              GitHub AI Trend Analyzer
            </div>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
              Built for reading market movement, not just listing repositories. Use the
              same page to move from macro pulse to repo explanation.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
            Real-time GitHub events
          </span>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
            Kafka + Spark + ClickHouse
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
            <Sparkles className="h-3.5 w-3.5 text-sky-500" />
            AI briefs and compare modes
          </span>
        </div>
      </div>
    </footer>
  );
}
