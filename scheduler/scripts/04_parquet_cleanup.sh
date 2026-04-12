#!/usr/bin/env bash
# =============================================================================
# 04_parquet_cleanup.sh
#
# SCHEDULE : 0 3 * * 0  (03:00 UTC every Sunday — after batch aggregation)
# PURPOSE  : Delete Parquet partitions older than RETENTION_DAYS (default 90).
#            Preserves the current day and yesterday (safety margin).
#            Logs each deleted partition for audit.
#
# DOMAIN   : Infrastructure layer — Parquet storage lifecycle management
#            Reads  : data/raw/event_date=*/  (partition directories)
#            Deletes: partitions where event_date < (TODAY - RETENTION_DAYS)
#
# IDEMPOTENT: YES — deleting already-deleted directories is a no-op.
# SAFETY   : Never deletes partitions from the past 2 days regardless of
#            RETENTION_DAYS value (prevents accidental same-day deletion).
# =============================================================================

SCRIPT_NAME="04_parquet_cleanup"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
RETENTION_DAYS="${1:-90}"           # default: keep 90 days of Parquet
PARQUET_BASE="${PARQUET_BASE_PATH:-${PROJECT_ROOT}/data/raw}"
SAFETY_DAYS=2                       # never delete partitions within last N days

exec >> "${LOG_FILE}" 2>&1

log_info "Starting Parquet cleanup (retention_days=${RETENTION_DAYS}, base=${PARQUET_BASE})"

# ── Guard: base path must exist ───────────────────────────────────────────────
if [[ ! -d "${PARQUET_BASE}" ]]; then
  log_warn "Parquet base path '${PARQUET_BASE}' does not exist — nothing to clean"
  exit 0
fi

# ── Compute cutoff date ───────────────────────────────────────────────────────
# Cutoff: any partition older than this date will be deleted
CUTOFF_DATE=$(date -u -d "${RETENTION_DAYS} days ago" '+%Y-%m-%d' 2>/dev/null \
              || date -u -v-"${RETENTION_DAYS}d" '+%Y-%m-%d')
SAFETY_DATE=$(date -u -d "${SAFETY_DAYS} days ago" '+%Y-%m-%d' 2>/dev/null \
              || date -u -v-"${SAFETY_DAYS}d" '+%Y-%m-%d')

log_info "Cutoff date: ${CUTOFF_DATE} | Safety floor: ${SAFETY_DATE}"

# ── Scan and delete expired partitions ───────────────────────────────────────
DELETED_COUNT=0
DELETED_BYTES=0
SKIPPED_COUNT=0

while IFS= read -r -d '' partition_dir; do
  # Extract date from directory name: event_date=YYYY-MM-DD
  dir_name=$(basename "${partition_dir}")
  event_date="${dir_name#event_date=}"

  # Validate date format
  if [[ ! "${event_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    log_warn "Skipping unexpected directory: ${partition_dir}"
    (( SKIPPED_COUNT++ )) || true
    continue
  fi

  # Safety: never delete partitions within the safety window
  if [[ "${event_date}" > "${SAFETY_DATE}" || "${event_date}" == "${SAFETY_DATE}" ]]; then
    continue
  fi

  # Check if older than cutoff
  if [[ "${event_date}" < "${CUTOFF_DATE}" ]]; then
    # Compute size before deletion for audit log
    PARTITION_BYTES=$(du -sb "${partition_dir}" 2>/dev/null | awk '{print $1}' || echo 0)
    PARTITION_MB=$(( PARTITION_BYTES / 1048576 ))

    rm -rf "${partition_dir}"
    log_info "Deleted partition: ${partition_dir} (${PARTITION_MB} MB)"
    (( DELETED_COUNT++ )) || true
    (( DELETED_BYTES += PARTITION_BYTES )) || true
  fi
done < <(find "${PARQUET_BASE}" -maxdepth 1 -type d -name "event_date=*" -print0 | sort -z)

DELETED_MB=$(( DELETED_BYTES / 1048576 ))
log_info "Parquet cleanup complete: deleted ${DELETED_COUNT} partitions (${DELETED_MB} MB total), skipped ${SKIPPED_COUNT}"
