#!/bin/bash
# Script pour arrêter Assistant Gazelle V5
# Usage: ./arreter.sh

echo "🛑 Arrêt d'Assistant Gazelle V5..."
echo ""

# Arrêter le backend (port 8000)
echo "🔧 Arrêt du backend..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "   ✅ Backend arrêté" || echo "   ⚠️  Backend déjà arrêté"

# Arrêter le frontend (port 5173)
echo "🎨 Arrêt du frontend..."
lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "   ✅ Frontend arrêté" || echo "   ⚠️  Frontend déjà arrêté"

# Nettoyer les fichiers PID
rm -f .backend.pid .frontend.pid 2>/dev/null

echo ""
echo "✅ Tous les services sont arrêtés"
