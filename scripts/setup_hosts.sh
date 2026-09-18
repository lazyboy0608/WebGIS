#!/bin/bash
set -e

echo "========================================================"
echo "  WebGIS - Cau Hinh Ten Mien seismicatlas.local (Linux)"
echo "========================================================"
echo ""

DOMAIN="seismicatlas.local"
IP="${1:-127.0.0.1}"

if grep -q "${DOMAIN}" /etc/hosts; then
    echo "[OK] Ten mien ${DOMAIN} da ton tai trong /etc/hosts."
else
    echo "Dang them '${IP} ${DOMAIN}' vao /etc/hosts..."
    echo -e "\n# WebGIS Local Domain\n${IP} ${DOMAIN}" | sudo tee -a /etc/hosts > /dev/null
    echo "[THANH CONG] Da them ${IP} ${DOMAIN} vao /etc/hosts!"
fi

echo ""
echo "Ban co the truy cap WebGIS tai: https://${DOMAIN}"
echo ""
