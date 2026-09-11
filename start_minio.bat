@echo off
title WebGIS-MinIO
echo Dang khoi dong MinIO Server tren port 9000 (Console 9001)...
set MINIO_ROOT_USER=minioadmin
set MINIO_ROOT_PASSWORD=minioadmin
d:\WebGIS\tools\minio\minio.exe server d:\WebGIS\storage\minio_data --console-address :9001 --address :9000
