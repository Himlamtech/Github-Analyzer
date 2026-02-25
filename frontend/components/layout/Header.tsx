import { GitBranch, Activity } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
            <GitBranch className="h-4 w-4 text-primary" />
          </div>
          <span className="text-gradient font-semibold tracking-tight">
            GitHub AI Trends
          </span>
        </div>

        {/* Live indicator */}
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
