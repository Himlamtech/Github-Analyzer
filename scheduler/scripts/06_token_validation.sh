#!/usr/bin/env bash
# =============================================================================
# 06_token_validation.sh
#
# SCHEDULE : 0 1 * * *  (01:00 UTC daily — before nightly batch starts)
# PURPOSE  : Validate all GitHub API tokens in GITHUB_API_TOKENS.
#            For each token:
#              - Call GET /rate_limit to check validity and remaining quota
#              - Log token fingerprint (first 8 + last 4 chars, masked)
#              - WARN if remaining < LOW_QUOTA_THRESHOLD (default 500)
#              - ERROR if token is invalid (HTTP 401)
#            Write summary to scheduler/state/token_status.json
#
# DOMAIN   : Infrastructure layer — GitHub API credential health check
#            Reads  : GITHUB_API_TOKENS env var (comma-separated)
#            Writes : scheduler/state/token_status.json
#
# IDEMPOTENT: YES — read-only GitHub API calls.
# SECURITY : Token values are NEVER logged. Only masked fingerprints are used.
# =============================================================================

SCRIPT_NAME="06_token_validation"
# shellcheck source=00_env.sh
source "$(dirname "$0")/00_env.sh"

LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}.log"
STATE_DIR="${PROJECT_ROOT}/scheduler/state"
STATE_FILE="${STATE_DIR}/token_status.json"
LOW_QUOTA_THRESHOLD="${1:-500}"
GITHUB_API_BASE="${GITHUB_API_BASE_URL:-https://api.github.com}"

exec >> "${LOG_FILE}" 2>&1

mkdir -p "${STATE_DIR}"

log_info "Starting GitHub token validation (low_quota_threshold=${LOW_QUOTA_THRESHOLD})"

# ── Parse token list ───────────────────────────────────────────────────────────
RAW_TOKENS="${GITHUB_API_TOKENS:-}"
if [[ -z "${RAW_TOKENS}" ]]; then
  log_error "GITHUB_API_TOKENS is not set — cannot validate"
  exit 1
fi

# Split on comma, strip whitespace, strip surrounding quotes
IFS=',' read -ra TOKEN_ARRAY <<< "${RAW_TOKENS//\"/}"

TOTAL=0
VALID=0
INVALID=0
LOW_QUOTA=0
RESULTS_JSON="["
FIRST=1

for token in "${TOKEN_ARRAY[@]}"; do
  token="${token// /}"   # strip spaces
  [[ -z "${token}" ]] && continue
  (( TOTAL++ )) || true

  # Masked fingerprint: first 8 chars + "..." + last 4 chars
  TOKEN_LEN=${#token}
  if (( TOKEN_LEN >= 12 )); then
    FINGERPRINT="${token:0:8}...${token: -4}"
  else
    FINGERPRINT="****"
  fi

  # Call GitHub /rate_limit
  HTTP_RESPONSE=$(
    curl -s -w "\n%{http_code}" \
      -H "Authorization: Bearer ${token}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "${GITHUB_API_BASE}/rate_limit" \
      2>/dev/null
  )
  HTTP_BODY=$(echo "${HTTP_RESPONSE}" | head -n -1)
  HTTP_CODE=$(echo "${HTTP_RESPONSE}" | tail -n 1)

  if [[ "${HTTP_CODE}" == "401" || "${HTTP_CODE}" == "403" ]]; then
    STATUS="invalid"
    REMAINING=0
    RESET_AT="unknown"
    log_error "Token ${FINGERPRINT} is INVALID (HTTP ${HTTP_CODE})"
    (( INVALID++ )) || true

  elif [[ "${HTTP_CODE}" == "200" ]]; then
    # Parse remaining and reset from JSON response
    REMAINING=$(echo "${HTTP_BODY}" | "${PYTHON}" -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('rate', {}).get('remaining', 0))
" 2>/dev/null || echo 0)

    RESET_EPOCH=$(echo "${HTTP_BODY}" | "${PYTHON}" -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('rate', {}).get('reset', 0))
" 2>/dev/null || echo 0)

    RESET_AT=$(date -u -d "@${RESET_EPOCH}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
               || date -u -r "${RESET_EPOCH}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null \
               || echo "unknown")

    if (( REMAINING < LOW_QUOTA_THRESHOLD )); then
      STATUS="low_quota"
      log_warn "Token ${FINGERPRINT} has LOW quota: ${REMAINING} remaining (resets ${RESET_AT})"
      (( LOW_QUOTA++ )) || true
    else
      STATUS="ok"
      log_info "Token ${FINGERPRINT} OK: ${REMAINING} remaining (resets ${RESET_AT})"
    fi
    (( VALID++ )) || true

  else
    STATUS="error"
    REMAINING=0
    RESET_AT="unknown"
    log_warn "Token ${FINGERPRINT} returned unexpected HTTP ${HTTP_CODE}"
    (( INVALID++ )) || true
  fi

  # Append to JSON array
  if [[ "${FIRST}" -eq 1 ]]; then
    FIRST=0
  else
    RESULTS_JSON+=","
  fi
  RESULTS_JSON+="{\"fingerprint\":\"${FINGERPRINT}\",\"status\":\"${STATUS}\",\"remaining\":${REMAINING},\"reset_at\":\"${RESET_AT}\"}"
done

RESULTS_JSON+="]"

# ── Write state file ──────────────────────────────────────────────────────────
cat > "${STATE_FILE}" <<JSON
{
  "checked_at": "$(ts)",
  "total_tokens": ${TOTAL},
  "valid": ${VALID},
  "invalid": ${INVALID},
  "low_quota": ${LOW_QUOTA},
  "low_quota_threshold": ${LOW_QUOTA_THRESHOLD},
  "tokens": ${RESULTS_JSON}
}
JSON

log_info "Token validation complete: total=${TOTAL} valid=${VALID} invalid=${INVALID} low_quota=${LOW_QUOTA}"

# Exit non-zero if ANY token is invalid (to surface in cron mail)
if (( INVALID > 0 )); then
  exit 1
fi
