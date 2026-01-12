#!/bin/bash
# Script de démarrage de l'API Assistant Gazelle V5

cd "$(dirname "$0")"

echo "🚀 Démarrage de l'API Assistant Gazelle V5..."
echo ""

export PYTHONPATH="$(pwd)"

python3 api/main.py
