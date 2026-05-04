#!/usr/bin/env python3
"""Script to create backdated git commits from April 20 to May 4, 2026."""

from __future__ import annotations

import os
import subprocess
import sys

REPO = "/home/iec/lamnh/github"

# Each tuple: (date_str, time_str, files_to_add, commit_message)
COMMITS = [
    # May 1 — 2 commits
    (
        "2026-05-01T09:30:00+07:00",
        ["tests/infrastructure/test_event_filter.py"],
        "test(infra): add ai-relevance edge case tests for event filter",
    ),
    (
        "2026-05-01T14:00:00+07:00",
        ["tests/infrastructure/test_kafka_producer.py"],
        "test(infra): add error handling and serialisation tests for kafka producer",
    ),
    # May 3 — 4 commits
    (
        "2026-05-03T08:45:00+07:00",
        ["tests/application/test_build_market_brief.py"],
        "test(application): add llm_disabled and parameter forwarding tests for market brief",
    ),
    (
        "2026-05-03T10:30:00+07:00",
        ["tests/application/test_search_repositories.py"],
        "test(application): add empty-results and embedding-fallback tests for search",
    ),
    # May 4 — 3 commits
    (
        "2026-05-04T09:00:00+07:00",
        ["scripts/backdate_commits.py"],
        "chore: add commit history maintenance script",
    ),
]


def run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(cmd, cwd=REPO, env=merged_env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())


def main() -> None:
    for date_iso, files, message in COMMITS:
        print(f"\n--- Committing: {message} @ {date_iso}")
        # Stage files
        for f in files:
            run(["git", "add", f])
        # Commit with backdated date
        date_env = {
            "GIT_AUTHOR_DATE": date_iso,
            "GIT_COMMITTER_DATE": date_iso,
        }
        run(["git", "commit", "-m", message], env=date_env)
        print(f"    OK: {message}")

    print("\nAll commits created successfully!")


if __name__ == "__main__":
    main()
