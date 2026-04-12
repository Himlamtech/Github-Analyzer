#!/usr/bin/env bash
# =============================================================================
# 02_kafka_lag_check.sh
#
# SCHEDULE : */5 * * * *  (every 5 minutes)
# PURPOSE  : Check Kafka consumer group lag for github_raw_events topic.
#            Logs a WARNING if total lag exceeds threshold (default 50,000).
#            Exports lag value to Prometheus pushgateway if PUSHGATEWAY_URL set.
#
# DOMAIN   : Infrastructure layer — Kafka consumer lag monitoring
#            Reads  : kafka consumer-groups describe (via kafka-consumer-groups.sh)
#            Writes : scheduler/logs/02_kafka_lag_check.log
#                     Prometheus pushgateway (optional)
#
# IDEMPOTENT: YES — read-only, no side effects.
# =============================================================================

SCRIPT_NAME="02_kafka_lag_check"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
LAG_THRESHOLD="${2:-50000}"        # default alert threshold
CONSUMER_GROUP="github_spark_consumer"
TOPIC="${KAFKA_TOPIC:-github_raw_events}"

exec >> "${LOG_FILE}" 2>&1

log_info "Starting Kafka lag check (topic=${TOPIC}, group=${CONSUMER_GROUP}, threshold=${LAG_THRESHOLD})"

# ── Guard: Kafka container running ───────────────────────────────────────────
if ! ${DOCKER_COMPOSE} ps kafka 2>/dev/null | grep -q "running\|Up"; then
  log_error "Kafka container not running — skipping lag check"
  exit 1
fi

# ── Fetch consumer group offsets ─────────────────────────────────────────────
# kafka-consumer-groups.sh is inside the Kafka container
LAG_OUTPUT=$(
  ${DOCKER_COMPOSE} exec -T kafka \
    /opt/kafka/bin/kafka-consumer-groups.sh \
      --bootstrap-server "localhost:9092" \
      --group "${CONSUMER_GROUP}" \
      --describe \
    2>/dev/null
) || {
  log_warn "kafka-consumer-groups.sh failed or consumer group '${CONSUMER_GROUP}' does not exist yet"
  exit 0
}

# ── Parse total lag (sum of LAG column, skip header/blank/UNKNOWN lines) ────
TOTAL_LAG=$(
  echo "${LAG_OUTPUT}" \
  | awk 'NR>1 && $6 ~ /^[0-9]+$/ { sum += $6 } END { print (sum == "" ? 0 : sum) }'
)

log_info "Consumer group '${CONSUMER_GROUP}' total lag: ${TOTAL_LAG}"

# ── Threshold check ───────────────────────────────────────────────────────────
if (( TOTAL_LAG > LAG_THRESHOLD )); then
  log_warn "LAG ALERT: ${TOTAL_LAG} > threshold ${LAG_THRESHOLD} — Spark streaming may be falling behind"
fi

# ── Optional: push to Prometheus pushgateway ─────────────────────────────────
if [[ -n "${PUSHGATEWAY_URL:-}" ]]; then
  cat <<METRICS | curl -s --data-binary @- "${PUSHGATEWAY_URL}/metrics/job/github_analyzer/instance/kafka_lag" > /dev/null
# HELP kafka_consumer_lag_total Total consumer group lag for github_raw_events
# TYPE kafka_consumer_lag_total gauge
kafka_consumer_lag_total{group="${CONSUMER_GROUP}",topic="${TOPIC}"} ${TOTAL_LAG}
METRICS
  log_info "Pushed kafka_consumer_lag_total=${TOTAL_LAG} to pushgateway"
fi
