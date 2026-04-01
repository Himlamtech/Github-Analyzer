#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/tectonic"
TECTONIC_BIN="${CACHE_DIR}/tectonic"
REPORT_TEX="${SCRIPT_DIR}/massive_data_mining_report.tex"

mkdir -p "${CACHE_DIR}"

if [[ ! -x "${TECTONIC_BIN}" ]]; then
  echo "Installing tectonic into ${CACHE_DIR}..."
  (
    cd "${CACHE_DIR}"
    curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
  )
fi

echo "Compiling ${REPORT_TEX}..."
"${TECTONIC_BIN}" -X compile "${REPORT_TEX}"

echo "PDF generated at ${SCRIPT_DIR}/massive_data_mining_report.pdf"
