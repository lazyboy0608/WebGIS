@echo off
title WebGIS-Redis
echo Dang khoi dong Redis Server tren port 6379...
cd /d d:\WebGIS\tools\redis
redis-server.exe redis.windows.conf
