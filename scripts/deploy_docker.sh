#!/bin/bash
set -e

echo "========================================================"
echo "  WebGIS Production Deployment (Docker Multi-Stage - Linux)"
echo "========================================================"
echo ""

# 1. Check Docker status
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH!"
    echo "Please install Docker Engine first: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "[ERROR] Docker daemon is not running or current user has no permissions!"
    echo "Try running: sudo systemctl start docker"
    echo "Or add user to docker group: sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi

# 2. Build and Start All Services
echo "[1/3] Building and starting all Docker containers..."
docker compose up -d --build --remove-orphans

# 3. Run Database Migrations
echo ""
echo "[2/3] Waiting for database to be ready and running Alembic migrations..."
sleep 5
docker compose exec -T data-serving alembic upgrade head

# 4. Get Host IP for LAN
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "[3/3] System successfully started!"
echo "========================================================"
echo "  WebGIS Web Server is running on Port 80!"
echo ""
echo "  Local Access:      http://localhost"
echo "  LAN Access:        http://${HOST_IP}"
echo "========================================================"
echo ""
