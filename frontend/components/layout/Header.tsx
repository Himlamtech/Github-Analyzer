import { GitBranch, Activity } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10">
            <GitBranch className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="text-gradient font-semibold tracking-tight">
              GitHub AI Market Pulse
            </div>
            <div className="text-[11px] text-muted-foreground">
              product view on the repo graph
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
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
