#!/usr/bin/env bash
# =============================================================================
# 08_health_check.sh
#
# SCHEDULE : */5 * * * *  (every 5 minutes)
# PURPOSE  : Comprehensive health check for all pipeline components:
#              1. Docker containers (kafka, clickhouse, prometheus, grafana)
#              2. Kafka topic existence + partition count
#              3. ClickHouse HTTP ping + table row counts
#              4. Parquet base path existence + recent partition check
#              5. FastAPI /health endpoint (if API container is running)
#            Writes aggregated health status to scheduler/state/health.json.
#            Exit code: 0 = all healthy, 1 = one or more checks failed.
#
# DOMAIN   : Infrastructure layer — pipeline health monitoring
#            Reads  : Docker service states, Kafka metadata, ClickHouse counts
#            Writes : scheduler/state/health.json
#
# IDEMPOTENT: YES — read-only checks.
# =============================================================================

SCRIPT_NAME="08_health_check"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
STATE_DIR="${PROJECT_ROOT}/scheduler/state"
STATE_FILE="${STATE_DIR}/health.json"

exec >> "${LOG_FILE}" 2>&1

mkdir -p "${STATE_DIR}"

log_info "Starting health check"

# ── Helpers ───────────────────────────────────────────────────────────────────
CHECKS_JSON="["
FIRST_CHECK=1
OVERALL_HEALTHY=1

record_check() {
  local name="$1"
  local status="$2"    # "ok" | "degraded" | "down"
  local detail="$3"

  if [[ "${FIRST_CHECK}" -eq 1 ]]; then FIRST_CHECK=0; else CHECKS_JSON+=","; fi
  CHECKS_JSON+="{\"name\":\"${name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}"

  if [[ "${status}" == "ok" ]]; then
    log_info "CHECK [${name}] ${status}: ${detail}"
  elif [[ "${status}" == "degraded" ]]; then
    log_warn "CHECK [${name}] ${status}: ${detail}"
    OVERALL_HEALTHY=0
  else
    log_error "CHECK [${name}] ${status}: ${detail}"
    OVERALL_HEALTHY=0
  fi
}

# ── 1. Docker container checks ────────────────────────────────────────────────
for service in kafka clickhouse prometheus grafana; do
  CONTAINER_STATE=$(
    ${DOCKER_COMPOSE} ps "${service}" 2>/dev/null \
    | awk 'NR>1 {print $0}' \
    | grep -oE "Up|running|healthy|exited|Exit" \
    | head -1
  )

  case "${CONTAINER_STATE}" in
    Up|running|healthy)
      record_check "docker_${service}" "ok" "container is ${CONTAINER_STATE}" ;;
    exited|Exit|"")
      record_check "docker_${service}" "down" "container is not running (state='${CONTAINER_STATE}')" ;;
    *)
      record_check "docker_${service}" "degraded" "container state='${CONTAINER_STATE}'" ;;
  esac
done

# ── 2. Kafka topic check ──────────────────────────────────────────────────────
TOPIC="${KAFKA_TOPIC:-github_raw_events}"
TOPIC_INFO=$(
  ${DOCKER_COMPOSE} exec -T kafka \
    /opt/kafka/bin/kafka-topics.sh \
      --bootstrap-server localhost:9092 \
      --describe \
      --topic "${TOPIC}" \
    2>/dev/null
) || true

if echo "${TOPIC_INFO}" | grep -q "PartitionCount"; then
  PARTITION_COUNT=$(echo "${TOPIC_INFO}" | grep -oE 'PartitionCount:[0-9]+' | grep -oE '[0-9]+' || echo "?")
  record_check "kafka_topic" "ok" "topic '${TOPIC}' exists with ${PARTITION_COUNT} partitions"
elif [[ -n "${TOPIC_INFO}" ]]; then
  record_check "kafka_topic" "degraded" "topic '${TOPIC}' info incomplete: ${TOPIC_INFO:0:100}"
else
  record_check "kafka_topic" "down" "topic '${TOPIC}' not found or Kafka unreachable"
fi

# ── 3. ClickHouse ping + row counts ──────────────────────────────────────────
CH_PING=$(
  ${DOCKER_COMPOSE} exec -T clickhouse \
    wget -q -O - http://localhost:8123/ping 2>/dev/null
) || true

if [[ "${CH_PING}" == "Ok." ]]; then
  record_check "clickhouse_ping" "ok" "HTTP /ping responded Ok."

  # Row counts for key tables
  for table in github_data repo_metadata repo_metadata_history repo_star_counts repo_activity_summary; do
    TABLE_EXISTS=$(
      ${DOCKER_COMPOSE} exec -T clickhouse \
        clickhouse-client \
          --user "${CLICKHOUSE_USER:-analyst}" \
          --password "${CLICKHOUSE_PASSWORD:-analyst_password}" \
          --database "${CLICKHOUSE_DATABASE:-github_analyzer}" \
          --query "EXISTS TABLE ${table}" \
        2>/dev/null
    ) || TABLE_EXISTS="0"

    if [[ "${TABLE_EXISTS}" != "1" ]]; then
      record_check "clickhouse_${table}" "degraded" "table is missing"
      continue
    fi

    ROW_COUNT=$(
      ${DOCKER_COMPOSE} exec -T clickhouse \
        clickhouse-client \
          --user "${CLICKHOUSE_USER:-analyst}" \
          --password "${CLICKHOUSE_PASSWORD:-analyst_password}" \
          --database "${CLICKHOUSE_DATABASE:-github_analyzer}" \
          --query "SELECT count() FROM ${table}" \
        2>/dev/null
    ) || ROW_COUNT="error"

    if [[ "${ROW_COUNT}" == "error" ]]; then
      record_check "clickhouse_${table}" "degraded" "row count query failed"
      continue
    fi

    record_check "clickhouse_${table}" "ok" "row_count=${ROW_COUNT}"
  done
else
  record_check "clickhouse_ping" "down" "HTTP /ping failed (response='${CH_PING}')"
fi

# ── 4. Parquet base path + recent partition ───────────────────────────────────
PARQUET_BASE="${PARQUET_BASE_PATH:-${PROJECT_ROOT}/data/raw}"

if [[ ! -d "${PARQUET_BASE}" ]]; then
  record_check "parquet_base_path" "down" "directory '${PARQUET_BASE}' does not exist"
else
  # Check most recent partition date
  LATEST_PARTITION=$(
    find "${PARQUET_BASE}" -maxdepth 1 -type d -name "event_date=*" \
    | sort | tail -1 | xargs -I{} basename {} 2>/dev/null || echo ""
  )

  if [[ -z "${LATEST_PARTITION}" ]]; then
    record_check "parquet_partitions" "degraded" "no partitions found in ${PARQUET_BASE}"
  else
    LATEST_DATE="${LATEST_PARTITION#event_date=}"
    TODAY=$(date -u '+%Y-%m-%d')
    YESTERDAY=$(date -u -d "yesterday" '+%Y-%m-%d' 2>/dev/null || date -u -v-1d '+%Y-%m-%d')

    if [[ "${LATEST_DATE}" == "${TODAY}" || "${LATEST_DATE}" == "${YESTERDAY}" ]]; then
      FILE_COUNT=$(find "${PARQUET_BASE}/${LATEST_PARTITION}" -name "*.parquet" | wc -l)
      record_check "parquet_partitions" "ok" "latest partition=${LATEST_DATE} files=${FILE_COUNT}"
    else
      record_check "parquet_partitions" "degraded" "latest partition=${LATEST_DATE} (expected today or yesterday)"
    fi
  fi
fi

# ── 5. FastAPI health endpoint ────────────────────────────────────────────────
API_URL="http://localhost:${API_PORT:-8000}/health"
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${API_URL}" 2>/dev/null || echo "000")

if [[ "${API_RESPONSE}" == "200" ]]; then
  record_check "fastapi_health" "ok" "GET /health returned 200"
elif [[ "${API_RESPONSE}" == "000" ]]; then
  record_check "fastapi_health" "degraded" "FastAPI not reachable at ${API_URL}"
else
  record_check "fastapi_health" "degraded" "GET /health returned HTTP ${API_RESPONSE}"
fi

# ── Write state file ──────────────────────────────────────────────────────────
CHECKS_JSON+="]"
OVERALL_STATUS=$([[ ${OVERALL_HEALTHY} -eq 1 ]] && echo "healthy" || echo "degraded")

cat > "${STATE_FILE}" <<JSON
{
  "checked_at": "$(ts)",
  "overall_status": "${OVERALL_STATUS}",
  "checks": ${CHECKS_JSON}
}
JSON

log_info "Health check complete — overall_status=${OVERALL_STATUS}"

exit $(( 1 - OVERALL_HEALTHY ))
