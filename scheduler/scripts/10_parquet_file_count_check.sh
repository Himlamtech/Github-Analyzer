#!/usr/bin/env bash
# =============================================================================
# 10_parquet_file_count_check.sh
#
# PURPOSE  : Alert when parquet file count or growth rate suggests small-file
#            explosion in the processor output path.
# =============================================================================

SCRIPT_NAME="10_parquet_file_count_check"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
STATE_DIR="${PROJECT_ROOT}/scheduler/state"
STATE_FILE="${STATE_DIR}/parquet_file_count.json"
PARQUET_BASE="${PARQUET_BASE_PATH:-${PROJECT_ROOT}/data/raw}"
MAX_PARQUET_FILES="${1:-200000}"
MAX_GROWTH_PER_HOUR="${2:-5000}"

mkdir -p "${STATE_DIR}"
exec >> "${LOG_FILE}" 2>&1

if [[ ! -d "${PARQUET_BASE}" ]]; then
  log_warn "Parquet base path '${PARQUET_BASE}' does not exist"
  exit 0
fi

CURRENT_COUNT=$(find "${PARQUET_BASE}" -type f -name "*.parquet" | wc -l | tr -d ' ')
NOW_EPOCH=$(date -u +%s)

PREVIOUS_COUNT=0
PREVIOUS_EPOCH=0
if [[ -f "${STATE_FILE}" ]]; then
  PREVIOUS_COUNT=$(STATE_FILE="${STATE_FILE}" ${PYTHON} <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

state_file = Path(os.environ["STATE_FILE"])
payload = json.loads(state_file.read_text())
print(int(payload.get("file_count", 0)))
PY
)
  PREVIOUS_EPOCH=$(STATE_FILE="${STATE_FILE}" ${PYTHON} <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

state_file = Path(os.environ["STATE_FILE"])
payload = json.loads(state_file.read_text())
print(int(payload.get("checked_at_epoch", 0)))
PY
)
fi

GROWTH=0
GROWTH_PER_HOUR=0
if [[ "${PREVIOUS_EPOCH}" -gt 0 && "${NOW_EPOCH}" -gt "${PREVIOUS_EPOCH}" ]]; then
  GROWTH=$(( CURRENT_COUNT - PREVIOUS_COUNT ))
  ELAPSED_SECONDS=$(( NOW_EPOCH - PREVIOUS_EPOCH ))
  GROWTH_PER_HOUR=$(( GROWTH * 3600 / ELAPSED_SECONDS ))
fi

STATE_FILE="${STATE_FILE}" CURRENT_COUNT="${CURRENT_COUNT}" NOW_EPOCH="${NOW_EPOCH}" GROWTH_PER_HOUR="${GROWTH_PER_HOUR}" ${PYTHON} <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

state_file = Path(os.environ["STATE_FILE"])
state_file.write_text(
    json.dumps(
        {
            "file_count": int(os.environ["CURRENT_COUNT"]),
            "checked_at_epoch": int(os.environ["NOW_EPOCH"]),
            "growth_per_hour": int(os.environ["GROWTH_PER_HOUR"]),
        },
        indent=2,
    )
)
PY

log_info "Parquet file count=${CURRENT_COUNT}, growth_per_hour=${GROWTH_PER_HOUR}"

if [[ "${CURRENT_COUNT}" -gt "${MAX_PARQUET_FILES}" ]]; then
  log_warn "PARQUET FILE ALERT: count ${CURRENT_COUNT} exceeds threshold ${MAX_PARQUET_FILES}"
fi

if [[ "${GROWTH_PER_HOUR}" -gt "${MAX_GROWTH_PER_HOUR}" ]]; then
  log_warn "PARQUET FILE GROWTH ALERT: growth_per_hour ${GROWTH_PER_HOUR} exceeds threshold ${MAX_GROWTH_PER_HOUR}"
fi

