"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BotMessageSquare, GitBranch, LayoutDashboard, Radar, Search } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: Radar },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/intelligence", label: "Intelligence", icon: Search },
  { href: "/chatbot", label: "Chatbot", icon: BotMessageSquare },
];

function isActiveRoute(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/85 bg-white/88 px-4 py-3 shadow-[0_18px_46px_-34px_rgba(15,23,42,0.24)] backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            aria-label="GitHub AI Trend Analyzer overview"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-gradient-to-br from-sky-100 via-white to-cyan-100 shadow-[0_12px_26px_-18px_rgba(14,165,233,0.35)]"
          >
            <GitBranch className="h-5 w-5 text-primary" />
          </Link>
          <div>
            <Link href="/" className="text-gradient text-lg font-semibold tracking-tight">
              GitHub AI Trend Analyzer
            </Link>
            <div className="hidden text-xs text-slate-500 lg:block">
              Real-time market intelligence for breakout repos, category shifts, and AI
              repository narratives
            </div>
          </div>
        </div>

        <nav className="hidden items-center gap-1 rounded-full border border-slate-200 bg-slate-50/85 p-1 lg:flex">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActiveRoute(pathname, item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium transition-colors ${
                  active
                    ? "bg-white text-slate-950 shadow-sm"
                    : "text-slate-600 hover:bg-white hover:text-slate-900"
                }`}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="flex items-center gap-2 rounded-full border border-emerald-200/80 bg-white/80 px-3 py-1.5 text-xs text-muted-foreground shadow-[0_14px_30px_-22px_rgba(16,185,129,0.35)]">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <Activity className="h-3 w-3" />
            <span>Live</span>
          </div>
        </div>

        <nav className="grid w-full grid-cols-4 gap-1 rounded-xl border border-slate-200 bg-slate-50/85 p-1 lg:hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActiveRoute(pathname, item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex min-h-10 items-center justify-center gap-1 rounded-lg px-2 text-xs font-medium transition-colors ${
                  active
                    ? "bg-white text-slate-950 shadow-sm"
                    : "text-slate-600 hover:bg-white hover:text-slate-900"
                }`}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
