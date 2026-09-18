#!/bin/bash
set -e

echo "========================================================"
echo "  WebGIS - Sinh Chung Chi SSL & CA Noi Bo (Linux)"
echo "========================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_PATH="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${ROOT_PATH}/backend/data-serving/.venv/bin/python" ]; then
    "${ROOT_PATH}/backend/data-serving/.venv/bin/python" "${SCRIPT_DIR}/generate_ssl_certs.py"
elif command -v python3 &>/dev/null; then
    python3 "${SCRIPT_DIR}/generate_ssl_certs.py"
else
    python "${SCRIPT_DIR}/generate_ssl_certs.py"
fi

echo ""
echo "[OK] Hoan tat sinh chung chi SSL!"
