#!/bin/bash
# Script pour garder Render actif (éviter cold starts)
# Lance un ping toutes les 10 minutes

while true; do
    curl -s https://assistant-gazelle-v5-api.onrender.com/health > /dev/null
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Ping Render OK"
    sleep 600  # 10 minutes
done
