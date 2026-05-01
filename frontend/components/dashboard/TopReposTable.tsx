"use client";

import Image from "next/image";
import { ExternalLink, GitFork, Sparkles, Star } from "lucide-react";

import { useTopRepos, useTopStarredRepos } from "@/hooks/useDashboard";
import { CATEGORY_COLORS, type Category } from "@/lib/types";
import { formatNumber, truncate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  category: Category;
  days: number;
  selectedRepo: string | null;
  onSelectRepo: (name: string) => void;
  limit?: number;
  title?: string;
  subtitle?: string;
  sortBy?: "stargazers_count" | "star_count_in_window";
  source?: "top-repos" | "top-starred-repos";
}

function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-border">
      <td className="py-3 pl-4">
        <div className="h-4 w-4 rounded bg-muted" />
      </td>
      <td className="py-3 px-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-muted" />
          <div>
            <div className="mb-1 h-3.5 w-32 rounded bg-muted" />
            <div className="h-3 w-48 rounded bg-muted" />
          </div>
        </div>
      </td>
      <td className="py-3 px-3"><div className="h-5 w-14 rounded-full bg-muted" /></td>
      <td className="py-3 px-3"><div className="h-4 w-16 rounded bg-muted" /></td>
      <td className="py-3 px-3"><div className="h-4 w-12 rounded bg-muted" /></td>
      <td className="py-3 pr-4"><div className="h-4 w-16 rounded bg-muted" /></td>
    </tr>
  );
}

export function TopReposTable({
  category,
  days,
  selectedRepo,
  onSelectRepo,
  limit = 20,
  title = "Repository Ranking Table",
  subtitle = "High-signal leaderboard with category and momentum context",
  sortBy = "star_count_in_window",
  source = "top-repos",
}: Props) {
  const topReposQuery = useTopRepos(category, days);
  const topStarredReposQuery = useTopStarredRepos(category, days);
  const activeQuery = source === "top-starred-repos" ? topStarredReposQuery : topReposQuery;
  const rows = [...(activeQuery.data ?? [])]
    .sort((left, right) => {
      if (sortBy === "stargazers_count") {
        return right.repo.stargazers_count - left.repo.stargazers_count;
      }
      return right.star_count_in_window - left.star_count_in_window;
    })
    .slice(0, limit);

  return (
    <div className="card-glow overflow-hidden rounded-[28px] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-sky-500" />
          <div>
            <h2 className="text-sm font-semibold">{title}</h2>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        <span className="text-xs text-muted-foreground">
          last {days} days · {rows.length} repos
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th className="py-2 pl-4 text-left font-medium">#</th>
              <th className="py-2 px-3 text-left font-medium">Repository</th>
              <th className="py-2 px-3 text-left font-medium">Category</th>
              <th className="py-2 px-3 text-left font-medium">Language</th>
              <th className="py-2 px-3 text-right font-medium">Stars</th>
              <th className="py-2 px-3 text-right font-medium">Forks</th>
              <th className="py-2 px-3 text-right font-medium">Watchers</th>
              <th className="py-2 pr-4 text-right font-medium">Window ★</th>
            </tr>
          </thead>
          <tbody>
            {activeQuery.isLoading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
              : rows.map((item, idx) => {
                  const repo = item.repo;
                  const color =
                    CATEGORY_COLORS[repo.category] ?? "#6b7280";
                  const isSelected = selectedRepo === repo.repo_full_name;

                  return (
                    <tr
                      key={repo.repo_id}
                      onClick={() => onSelectRepo(repo.repo_full_name)}
                      className={cn(
                        "cursor-pointer border-b border-border/60 transition-colors",
                        isSelected
                          ? "bg-primary/8"
                          : "hover:bg-muted/40",
                      )}
                    >
                      {/* Rank */}
                      <td className="py-3 pl-4 text-xs font-mono text-muted-foreground">
                        {idx + 1}
                      </td>

                      {/* Repo info */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2.5">
                          <Image
                            src={repo.owner_avatar_url || `https://avatars.githubusercontent.com/u/0`}
                            alt={repo.owner_login}
                            width={28}
                            height={28}
                            className="rounded-full"
                            unoptimized
                          />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <a
                                href={repo.html_url}
                                target="_blank"
                                rel="noreferrer"
                                className="truncate font-medium hover:text-primary"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {repo.repo_full_name}
                              </a>
                              <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" />
                            </div>
                            {repo.description && (
                              <p className="truncate text-xs text-muted-foreground">
                                {truncate(repo.description, 60)}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
                          style={{ backgroundColor: color }}
                        >
                          {repo.category}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-xs text-muted-foreground">
                        {repo.primary_language || "Unknown"}
                      </td>

                      <td className="py-3 px-3 text-right font-mono text-xs">
                        <div className="flex items-center justify-end gap-1">
                          <Star className="h-3 w-3 text-amber-400" />
                          {formatNumber(repo.stargazers_count)}
                        </div>
                      </td>

                      {/* Forks */}
                      <td className="py-3 px-3 text-right font-mono text-xs text-muted-foreground">
                        <div className="flex items-center justify-end gap-1">
                          <GitFork className="h-3 w-3" />
                          {formatNumber(repo.forks_count)}
                        </div>
                      </td>

                      <td className="py-3 px-3 text-right font-mono text-xs text-muted-foreground">
                        {formatNumber(repo.watchers_count)}
                      </td>

                      <td className="py-3 pr-4 text-right font-mono text-xs text-emerald-400">
                        +{formatNumber(item.star_count_in_window)}
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
