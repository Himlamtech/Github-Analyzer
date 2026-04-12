#!/usr/bin/env bash
# =============================================================================
# 05_clickhouse_optimize.sh
#
# SCHEDULE : 0 4 * * 0  (04:00 UTC every Sunday — after batch aggregation)
# PURPOSE  : Force OPTIMIZE TABLE FINAL on key analytical tables to
#            trigger immediate merges and collapse deduplicated state.
#
#            ClickHouse ReplacingMergeTree deduplicates lazily during background
#            merges. OPTIMIZE FINAL forces an immediate merge so that SELECT
#            queries return deduplicated results without needing FINAL qualifier.
#
# DOMAIN   : Infrastructure layer — ClickHouse table maintenance
#            Modifies: github_analyzer.repo_metadata
#                      github_analyzer.repo_metadata_history
#                      github_analyzer.repo_star_counts
#                      github_analyzer.repo_activity_summary
#
# IDEMPOTENT: YES — OPTIMIZE on an already-merged table is a no-op.
# NOTE     : OPTIMIZE FINAL can be I/O intensive. Run during low-traffic window.
# =============================================================================

SCRIPT_NAME="05_clickhouse_optimize"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
CH_DATABASE="${CLICKHOUSE_DATABASE:-github_analyzer}"
CH_USER="${CLICKHOUSE_USER:-analyst}"
CH_PASSWORD="${CLICKHOUSE_PASSWORD:-analyst_password}"

# Tables to optimize when present in the target database.
TABLES_TO_OPTIMIZE=(
  "repo_metadata"
  "repo_metadata_history"
  "repo_star_counts"
  "repo_activity_summary"
)

exec >> "${LOG_FILE}" 2>&1

log_info "Starting ClickHouse OPTIMIZE FINAL (database=${CH_DATABASE})"

# ── Guard: ClickHouse reachable ───────────────────────────────────────────────
if ! ${DOCKER_COMPOSE} exec -T clickhouse \
    wget -q --spider http://localhost:8123/ping > /dev/null 2>&1; then
  log_error "ClickHouse not reachable — aborting optimize"
  exit 1
fi

# ── Run OPTIMIZE FINAL on each table ─────────────────────────────────────────
FAILED=0

for table in "${TABLES_TO_OPTIMIZE[@]}"; do
  TABLE_EXISTS=$(
    ${DOCKER_COMPOSE} exec -T clickhouse \
      clickhouse-client \
        --user "${CH_USER}" \
        --password "${CH_PASSWORD}" \
        --database "${CH_DATABASE}" \
        --query "EXISTS TABLE ${table}" \
      2>/dev/null
  ) || TABLE_EXISTS="0"

  if [[ "${TABLE_EXISTS}" != "1" ]]; then
    log_warn "Skipping OPTIMIZE for missing table ${CH_DATABASE}.${table}"
    continue
  fi

  log_info "Running OPTIMIZE TABLE FINAL on ${CH_DATABASE}.${table} …"
  START=$(date +%s)

  OUTPUT=$(
    ${DOCKER_COMPOSE} exec -T clickhouse \
      clickhouse-client \
        --user "${CH_USER}" \
        --password "${CH_PASSWORD}" \
        --database "${CH_DATABASE}" \
        --query "OPTIMIZE TABLE ${table} FINAL" \
      2>&1
  )
  EXIT_CODE=$?
  ELAPSED=$(( $(date +%s) - START ))

  if [[ ${EXIT_CODE} -eq 0 ]]; then
    log_info "OPTIMIZE completed for ${table} in ${ELAPSED}s"
  else
    log_error "OPTIMIZE failed for ${table} (exit=${EXIT_CODE}): ${OUTPUT}"
    (( FAILED++ )) || true
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
if [[ ${FAILED} -gt 0 ]]; then
  log_error "ClickHouse optimize finished with ${FAILED} failure(s)"
  exit 1
fi

log_info "ClickHouse optimize complete — all tables merged"
