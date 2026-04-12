#!/usr/bin/env bash
# =============================================================================
# 07_repo_metadata_refresh.sh
#
# SCHEDULE : 0 6 * * *  (06:00 UTC daily — after nightly batch completes)
# PURPOSE  : Re-fetch full repository metadata for all repos stored in
#            data/repos/*.json using the GitHub Repos API.
#            Before refreshing, run repo catalog discovery so newly discovered
#            high-star repositories enter the refresh set automatically.
#            Maps the response through repo_fetcher.map_repo_response() to
#            produce the canonical 45-field schema.
#
# DOMAIN   : Infrastructure layer — repository metadata enrichment
#            Reads  : data/repos/*.json  (existing repo snapshots)
#            Writes : data/repos/<owner>__<name>.json  (updated 45-field schema)
#                     scheduler/state/repo_refresh_summary.json
#            Side effects:
#                     - syncs latest repo metadata into ClickHouse
#                     - appends repo metadata history snapshots in ClickHouse
#
# IDEMPOTENT: YES — overwriting with the same (or newer) data is safe.
# RATE LIMIT: Uses the first valid token from GITHUB_API_TOKENS.
#             Each refresh = 1 API call. Sleeps 1s between calls.
# =============================================================================

SCRIPT_NAME="07_repo_metadata_refresh"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
STATE_DIR="${PROJECT_ROOT}/scheduler/state"
STATE_FILE="${STATE_DIR}/repo_refresh_summary.json"
REPOS_DIR="${PROJECT_ROOT}/data/repos"
SLEEP_BETWEEN_CALLS="${1:-1}"

exec >> "${LOG_FILE}" 2>&1

mkdir -p "${STATE_DIR}"

log_info "Starting repo metadata refresh (repos_dir=${REPOS_DIR})"

# ── Seed newly discovered repositories before refreshing known snapshots ─────
log_info "Running repo catalog discovery before refresh"
if ! "${PYTHON}" -m src.application.use_cases.discover_repo_catalog; then
  log_error "Repo catalog discovery failed"
  exit 1
fi

# ── Guard: repos directory must exist ────────────────────────────────────────
if [[ ! -d "${REPOS_DIR}" ]]; then
  log_warn "Repos directory '${REPOS_DIR}' not found — nothing to refresh"
  exit 0
fi

# ── Pick first valid token ────────────────────────────────────────────────────
RAW_TOKENS="${GITHUB_API_TOKENS:-}"
FIRST_TOKEN=""
IFS=',' read -ra TOKEN_ARRAY <<< "${RAW_TOKENS//\"/}"
for t in "${TOKEN_ARRAY[@]}"; do
  t="${t// /}"
  [[ -n "${t}" ]] && FIRST_TOKEN="${t}" && break
done

if [[ -z "${FIRST_TOKEN}" ]]; then
  log_error "No GitHub token available — cannot refresh repo metadata"
  exit 1
fi

# ── Refresh all repos via repo_fetcher.map_repo_response() ───────────────────
RESULT=$(
  "${PYTHON}" - <<PYEOF
import sys, os, json
os.chdir("${PROJECT_ROOT}")
sys.path.insert(0, "${PROJECT_ROOT}")

import asyncio
from pathlib import Path
from src.infrastructure.github.repo_fetcher import fetch_repo, map_repo_response

REPOS_DIR = Path("${REPOS_DIR}")
TOKEN = "${FIRST_TOKEN}"
SLEEP = float("${SLEEP_BETWEEN_CALLS}")

async def main() -> dict:
    refreshed, failed, skipped = 0, 0, 0

    repo_files = sorted(
        f for f in REPOS_DIR.glob("*.json")
        if "summary" not in f.name
    )

    for rank, repo_file in enumerate(repo_files, start=1):
        try:
            data = json.loads(repo_file.read_text())
        except Exception as exc:
            print(f"[SKIP] Cannot read {repo_file.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        full_name = data.get("full_name") or repo_file.stem.replace("__", "/", 1)
        print(f"[INFO] Refreshing {full_name} (rank={rank}) …", file=sys.stderr)

        try:
            mapped = await fetch_repo(full_name, TOKEN, rank=rank)
        except Exception as exc:
            print(f"[ERROR] {full_name}: {exc}", file=sys.stderr)
            failed += 1
            await asyncio.sleep(SLEEP)
            continue

        # Preserve original fetch_at if present
        if "fetched_at" in data and "fetched_at" not in mapped:
            mapped["fetched_at"] = data["fetched_at"]

        # Atomic write: .tmp → rename
        tmp = repo_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(mapped, indent=2, ensure_ascii=False))
        tmp.rename(repo_file)

        stars = mapped.get("stargazers_count", "?")
        subs  = mapped.get("subscribers_count", "?")
        print(
            f"[OK]  {full_name} — stars={stars} subscribers={subs}",
            file=sys.stderr,
        )
        refreshed += 1
        await asyncio.sleep(SLEEP)

    return {"refreshed": refreshed, "failed": failed, "skipped": skipped}

counts = asyncio.run(main())
print(json.dumps(counts))
PYEOF
)

EXIT_CODE=$?

if [[ ${EXIT_CODE} -ne 0 ]]; then
  log_error "repo_fetcher failed (exit=${EXIT_CODE})"
  exit ${EXIT_CODE}
fi

REFRESHED=$(echo "${RESULT}" | "${PYTHON}" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['refreshed'])")
FAILED=$(echo "${RESULT}"    | "${PYTHON}" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['failed'])")
SKIPPED=$(echo "${RESULT}"   | "${PYTHON}" -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['skipped'])")

# ── Rebuild summary file ──────────────────────────────────────────────────────
"${PYTHON}" - <<PYEOF
import json, sys, os
os.chdir("${PROJECT_ROOT}")
sys.path.insert(0, "${PROJECT_ROOT}")

from pathlib import Path
from datetime import datetime, timezone

repos_dir = Path("${REPOS_DIR}")
summaries = []

for f in sorted(repos_dir.glob("*.json")):
    if "summary" in f.name:
        continue
    try:
        data = json.loads(f.read_text())
        summaries.append({
            "rank":              data.get("rank"),
            "full_name":         data.get("full_name", f.stem.replace("__", "/")),
            "description":       data.get("description"),
            "language":          data.get("language"),
            "topics":            data.get("topics", []),
            "stargazers_count":  data.get("stargazers_count", 0),
            "forks_count":       data.get("forks_count", 0),
            "subscribers_count": data.get("subscribers_count", 0),
            "network_count":     data.get("network_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
            "license":           (data.get("license") or {}).get("spdx_id"),
            "archived":          data.get("archived", False),
            "pushed_at":         data.get("pushed_at"),
            "refreshed_at":      data.get("refreshed_at"),
            "html_url":          data.get("html_url"),
        })
    except Exception as exc:
        print(f"[WARN] Cannot read {f.name}: {exc}", file=sys.stderr)

summaries.sort(key=lambda x: (x.get("stargazers_count") or 0), reverse=True)
for i, s in enumerate(summaries, start=1):
    s["rank"] = i

summary = {
    "updated_at":  datetime.now(timezone.utc).isoformat(),
    "total_repos": len(summaries),
    "repos":       summaries,
}
out_path = repos_dir / "top5_ai_repos_summary.json"
out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"Summary written: {len(summaries)} repos → {out_path}", file=sys.stderr)
PYEOF

# ── Sync latest + history snapshots into ClickHouse ──────────────────────────
log_info "Syncing refreshed repo metadata into ClickHouse"
if ! "${PYTHON}" -m src.application.use_cases.sync_repo_metadata; then
  log_error "Repo metadata sync failed after refresh"
  exit 1
fi

log_info "Repo metadata refresh complete: refreshed=${REFRESHED} failed=${FAILED} skipped=${SKIPPED}"

cat > "${STATE_FILE}" <<JSON
{
  "refreshed_at": "$(ts)",
  "refreshed": ${REFRESHED},
  "failed": ${FAILED},
  "skipped": ${SKIPPED}
}
JSON

if (( FAILED > 0 )); then
  exit 1
fi
