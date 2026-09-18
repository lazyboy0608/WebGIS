#!/bin/bash
set -e

echo "========================================================"
echo "  WebGIS - Cai Dat Root CA Vao Linux System (Ubuntu/Debian)"
echo "========================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_PATH="${SCRIPT_DIR}/../certs/rootCA.crt"

if [ ! -f "${CERT_PATH}" ]; then
    echo "[ERROR] Khong tim thay tep Root CA tai: ${CERT_PATH}"
    echo "Vui long chay ./scripts/generate_ssl_certs.sh truoc."
    exit 1
fi

echo "Dang cai dat Root CA vao /usr/local/share/ca-certificates/..."
sudo cp "${CERT_PATH}" /usr/local/share/ca-certificates/webgis_root_ca.crt
sudo update-ca-certificates

echo ""
echo "========================================================"
echo "  [THANH CONG] Da tin cay WebGIS Root CA tren Linux!"
echo "========================================================"
echo ""
