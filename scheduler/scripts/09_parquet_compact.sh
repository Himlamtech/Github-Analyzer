#!/usr/bin/env bash
# =============================================================================
# 09_parquet_compact.sh
#
# PURPOSE  : Compact legacy small parquet files for a single event_date
#            partition into larger snappy-compressed files.
# USAGE    : ./scheduler/scripts/09_parquet_compact.sh YYYY-MM-DD [MAX_ROWS]
# =============================================================================

SCRIPT_NAME="09_parquet_compact"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
PARQUET_BASE="${PARQUET_BASE_PATH:-${PROJECT_ROOT}/data/raw}"
EVENT_DATE="${1:-}"
MAX_ROWS_PER_FILE="${2:-50000}"

exec >> "${LOG_FILE}" 2>&1

if [[ -z "${EVENT_DATE}" ]]; then
  log_error "Usage: ${0} YYYY-MM-DD [MAX_ROWS_PER_FILE]"
  exit 1
fi

TARGET_DIR="${PARQUET_BASE}/event_date=${EVENT_DATE}"
if [[ ! -d "${TARGET_DIR}" ]]; then
  log_warn "Partition '${TARGET_DIR}' does not exist"
  exit 0
fi

log_info "Starting parquet compaction for ${TARGET_DIR} (max_rows_per_file=${MAX_ROWS_PER_FILE})"

TARGET_DIR="${TARGET_DIR}" MAX_ROWS_PER_FILE="${MAX_ROWS_PER_FILE}" ${PYTHON} <<'PY'
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

target_dir = Path(os.environ["TARGET_DIR"])
max_rows_per_file = int(os.environ["MAX_ROWS_PER_FILE"])

for event_type_dir in sorted(target_dir.glob("event_type=*")):
    parquet_files = sorted(path for path in event_type_dir.glob("*.parquet") if path.is_file())
    if len(parquet_files) <= 1:
        continue

    tables = [pq.read_table(parquet_file) for parquet_file in parquet_files]  # type: ignore[no-untyped-call]
    combined = pa.concat_tables(tables, promote_options="default")
    tmp_dir = event_type_dir / ".compact_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    total_rows = combined.num_rows
    file_index = 0
    offset = 0
    while offset < total_rows:
        chunk = combined.slice(offset, max_rows_per_file)
        pq.write_table(  # type: ignore[no-untyped-call]
            chunk,
            tmp_dir / f"compacted-{file_index:05d}.parquet",
            compression="snappy",
        )
        offset += max_rows_per_file
        file_index += 1

    for parquet_file in parquet_files:
        parquet_file.unlink()
    for compacted_file in sorted(tmp_dir.glob("*.parquet")):
        compacted_file.replace(event_type_dir / compacted_file.name)
    tmp_dir.rmdir()
PY

log_info "Completed parquet compaction for ${TARGET_DIR}"

