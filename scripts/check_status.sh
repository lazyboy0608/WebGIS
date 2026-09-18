#!/bin/bash

echo "========================================================"
echo "  WebGIS Production System Health & Status Check (Linux)"
echo "========================================================"
echo ""

# 1. Container Status
echo "==> 1. Container Running Status:"
docker compose ps
echo ""

# 2. Resource Usage
echo "==> 2. Container Resource Usage (CPU & RAM):"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}"
echo ""

# 3. Database Migration Status
echo "==> 3. PostGIS Database Migration Status:"
docker compose exec -T data-serving alembic current
echo ""

# 4. Host LAN IP & Access Endpoints
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo "========================================================"
echo "  WebGIS Web Server Access Endpoints:"
echo "  - Local URL:   http://localhost"
echo "  - LAN WebGIS:  http://${HOST_IP}"
echo "  - Admin Panel: http://${HOST_IP}/admin"
echo "========================================================"
echo ""
