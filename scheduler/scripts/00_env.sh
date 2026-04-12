#!/usr/bin/env bash
# =============================================================================
# 00_env.sh — Shared environment bootstrap for all scheduler scripts
# Source this file at the top of every scheduler script:
#   source "$(dirname "$0")/00_env.sh"
# =============================================================================

set -euo pipefail

# ── Project root (absolute, resolved from this file's location) ──────────────
export PROJECT_ROOT
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Load .env ─────────────────────────────────────────────────────────────────
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] .env not found at ${ENV_FILE}" >&2
  exit 1
fi

# Export only non-comment, non-empty lines
set -a
# shellcheck disable=SC1090
while IFS= read -r line; do
  [[ "${line}" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line//[[:space:]]/}" ]] && continue
  export "${line?}"
done < "${ENV_FILE}"
set +a

# ── Conda python interpreter ──────────────────────────────────────────────────
CONDA_BASE="${CONDA_PREFIX:-/media/aiz/0836a33f-812f-4e69-a6f9-784fe732c6d5/miniconda3}"
export PYTHON="${CONDA_BASE}/envs/data/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "[ERROR] Python not found at ${PYTHON}" >&2
  exit 1
fi

# ── Log directory ─────────────────────────────────────────────────────────────
export LOG_DIR="${PROJECT_ROOT}/scheduler/logs"
mkdir -p "${LOG_DIR}"

# ── Docker compose helper ─────────────────────────────────────────────────────
export DOCKER_COMPOSE="docker compose -f ${PROJECT_ROOT}/docker-compose.yml"

# ── Timestamp helper ──────────────────────────────────────────────────────────
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
export -f ts

# ── Structured log helpers ────────────────────────────────────────────────────
log_info()  { echo "{\"level\":\"info\",  \"ts\":\"$(ts)\", \"script\":\"${SCRIPT_NAME:-unknown}\", \"msg\":\"$*\"}" ; }
log_warn()  { echo "{\"level\":\"warn\",  \"ts\":\"$(ts)\", \"script\":\"${SCRIPT_NAME:-unknown}\", \"msg\":\"$*\"}" >&2; }
log_error() { echo "{\"level\":\"error\", \"ts\":\"$(ts)\", \"script\":\"${SCRIPT_NAME:-unknown}\", \"msg\":\"$*\"}" >&2; }
export -f log_info log_warn log_error
