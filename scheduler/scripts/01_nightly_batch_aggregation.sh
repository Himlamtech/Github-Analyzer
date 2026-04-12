#!/usr/bin/env bash
# =============================================================================
# 01_nightly_batch_aggregation.sh
#
# SCHEDULE : 0 2 * * *  (02:00 UTC daily — after midnight data is settled)
# PURPOSE  : Run GithubBatchJob: read Parquet archive → compute daily
#            repo_star_counts + weekly repo_activity_summary → write to
#            ClickHouse (ReplacingMergeTree auto-deduplicates re-runs).
#
# DOMAIN   : Infrastructure layer → spark/batch_job.py
#            Reads  : data/raw/event_date=*/event_type=*/*.parquet
#            Writes : ClickHouse github_analyzer.repo_star_counts
#                              github_analyzer.repo_activity_summary
#
# IDEMPOTENT: YES — ReplacingMergeTree keeps highest computed_at/updated_at.
#             Re-running the same date range is safe.
# =============================================================================

SCRIPT_NAME="01_nightly_batch_aggregation"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
LOOKBACK_DAYS="${1:-7}"   # default: aggregate last 7 days

exec >> "${LOG_FILE}" 2>&1

log_info "Starting nightly batch aggregation (lookback_days=${LOOKBACK_DAYS})"

# ── Guard: check ClickHouse is reachable ──────────────────────────────────────
if ! ${DOCKER_COMPOSE} exec -T clickhouse \
    wget -q --spider http://localhost:8123/ping > /dev/null 2>&1; then
  log_error "ClickHouse not reachable — aborting batch aggregation"
  exit 1
fi

# ── Guard: check Parquet data exists for yesterday ────────────────────────────
YESTERDAY=$(date -u -d "yesterday" '+%Y-%m-%d' 2>/dev/null || date -u -v-1d '+%Y-%m-%d')
PARQUET_YESTERDAY="${PARQUET_BASE_PATH:-${PROJECT_ROOT}/data/raw}/event_date=${YESTERDAY}"

if [[ ! -d "${PARQUET_YESTERDAY}" ]]; then
  log_warn "No Parquet partition found for ${YESTERDAY} at ${PARQUET_YESTERDAY} — skipping"
  exit 0
fi

# ── Run Spark batch job ───────────────────────────────────────────────────────
START_TIME=$(date +%s)

"${PYTHON}" - <<PYEOF
import sys, os
os.chdir("${PROJECT_ROOT}")
sys.path.insert(0, "${PROJECT_ROOT}")

from src.infrastructure.config import get_settings
from src.infrastructure.observability.logging_config import configure_logging
from src.infrastructure.spark.session_factory import create_spark_session
from src.infrastructure.spark.batch_job import GithubBatchJob

settings = get_settings()
configure_logging(settings.log_level)

spark = create_spark_session(settings)
job = GithubBatchJob(spark=spark, settings=settings)
job.run(lookback_days=${LOOKBACK_DAYS})
spark.stop()
print("Batch job completed successfully")
PYEOF

EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [[ ${EXIT_CODE} -eq 0 ]]; then
  log_info "Batch aggregation completed in ${ELAPSED}s"
else
  log_error "Batch aggregation failed with exit code ${EXIT_CODE} after ${ELAPSED}s"
  exit ${EXIT_CODE}
fi
