#!/usr/bin/env bash
# =============================================================================
# 03_data_freshness_check.sh
#
# SCHEDULE : */5 * * * *  (every 5 minutes)
# PURPOSE  : Query ClickHouse for max(created_at) in github_data table.
#            Computes staleness in seconds and writes it to:
#              1. A local state file (scheduler/state/data_freshness.json)
#              2. Prometheus pushgateway (if PUSHGATEWAY_URL is set)
#            Logs WARNING if staleness exceeds threshold (default 600s / 10 min).
#
# DOMAIN   : Infrastructure layer — ClickHouse data freshness probe
#            Reads  : ClickHouse github_analyzer.github_data
#            Writes : scheduler/state/data_freshness.json
#                     Prometheus pushgateway (optional)
#
# IDEMPOTENT: YES — read-only query, state file is overwritten each run.
# =============================================================================

SCRIPT_NAME="03_data_freshness_check"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
STATE_DIR="${PROJECT_ROOT}/scheduler/state"
STATE_FILE="${STATE_DIR}/data_freshness.json"
STALE_THRESHOLD_SECONDS="${1:-600}"   # default: alert if data is > 10 min old

exec >> "${LOG_FILE}" 2>&1

mkdir -p "${STATE_DIR}"

log_info "Starting data freshness check (stale_threshold=${STALE_THRESHOLD_SECONDS}s)"

# ── Guard: ClickHouse reachable ───────────────────────────────────────────────
if ! ${DOCKER_COMPOSE} exec -T clickhouse \
    wget -q --spider http://localhost:8123/ping > /dev/null 2>&1; then
  log_error "ClickHouse not reachable — skipping freshness check"
  exit 1
fi

# ── Query max(created_at) from github_data ───────────────────────────────────
MAX_CREATED_AT=$(
  ${DOCKER_COMPOSE} exec -T clickhouse \
    clickhouse-client \
      --user "${CLICKHOUSE_USER:-analyst}" \
      --password "${CLICKHOUSE_PASSWORD:-analyst_password}" \
      --database "${CLICKHOUSE_DATABASE:-github_analyzer}" \
      --query "SELECT formatDateTime(max(created_at), '%Y-%m-%d %H:%M:%S', 'UTC') FROM github_data" \
    2>/dev/null
) || {
  log_warn "ClickHouse query failed — table may be empty or not yet initialized"
  exit 0
}

# Trim whitespace
MAX_CREATED_AT="${MAX_CREATED_AT//[[:space:]]/}"

if [[ -z "${MAX_CREATED_AT}" || "${MAX_CREATED_AT}" == "0000-00-00 00:00:00" ]]; then
  log_warn "github_data table appears empty — no events ingested yet"
  exit 0
fi

# ── Compute staleness ─────────────────────────────────────────────────────────
NOW_EPOCH=$(date -u +%s)
MAX_EPOCH=$(date -u -d "${MAX_CREATED_AT}" +%s 2>/dev/null || date -u -j -f "%Y-%m-%d %H:%M:%S" "${MAX_CREATED_AT}" +%s)
STALENESS_SECONDS=$(( NOW_EPOCH - MAX_EPOCH ))

log_info "Latest event: ${MAX_CREATED_AT} UTC | staleness: ${STALENESS_SECONDS}s"

# ── Threshold check ───────────────────────────────────────────────────────────
if (( STALENESS_SECONDS > STALE_THRESHOLD_SECONDS )); then
  log_warn "DATA FRESHNESS ALERT: last event was ${STALENESS_SECONDS}s ago (threshold=${STALE_THRESHOLD_SECONDS}s) — pipeline may be stalled"
fi

# ── Write state file ──────────────────────────────────────────────────────────
cat > "${STATE_FILE}" <<JSON
{
  "checked_at": "$(ts)",
  "max_created_at": "${MAX_CREATED_AT}",
  "staleness_seconds": ${STALENESS_SECONDS},
  "threshold_seconds": ${STALE_THRESHOLD_SECONDS},
  "is_stale": $(( STALENESS_SECONDS > STALE_THRESHOLD_SECONDS ? 1 : 0 ))
}
JSON

log_info "State written to ${STATE_FILE}"

# ── Optional: push to Prometheus pushgateway ─────────────────────────────────
if [[ -n "${PUSHGATEWAY_URL:-}" ]]; then
  cat <<METRICS | curl -s --data-binary @- "${PUSHGATEWAY_URL}/metrics/job/github_analyzer/instance/data_freshness" > /dev/null
# HELP github_data_freshness_seconds Seconds since last event was ingested into ClickHouse
# TYPE github_data_freshness_seconds gauge
github_data_freshness_seconds{database="${CLICKHOUSE_DATABASE:-github_analyzer}",table="github_data"} ${STALENESS_SECONDS}
METRICS
  log_info "Pushed github_data_freshness_seconds=${STALENESS_SECONDS} to pushgateway"
fi
