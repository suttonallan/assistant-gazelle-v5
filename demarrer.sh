#!/bin/bash
# Script de démarrage simplifié pour Assistant Gazelle V5
# Usage: ./demarrer.sh

echo "🚀 Démarrage d'Assistant Gazelle V5..."
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "api/main.py" ]; then
    echo "❌ Erreur: Exécute ce script depuis le dossier assistant-gazelle-v5"
    exit 1
fi

# Vérifier que python3 est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Erreur: python3 n'est pas installé"
    exit 1
fi

# Vérifier que npm est installé
if ! command -v npm &> /dev/null; then
    echo "❌ Erreur: npm n'est pas installé"
    exit 1
fi

echo "✅ Vérifications OK"
echo ""

# Démarrer le backend en arrière-plan
echo "🔧 Démarrage du backend (port 8000)..."
python3 -m uvicorn api.main:app --reload --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
echo ""

# Attendre que le backend soit prêt
echo "⏳ Attente du backend..."
sleep 3

# Vérifier que le backend fonctionne
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend opérationnel"
else
    echo "⚠️  Backend en cours de démarrage (vérifier backend.log si problème)"
fi
echo ""

# Démarrer le frontend
echo "🎨 Démarrage du frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
echo "   PID: $FRONTEND_PID"
echo ""

# Attendre un peu pour le frontend
sleep 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Assistant Gazelle V5 démarré !"
echo ""
echo "📍 URLs d'accès:"
echo "   Frontend: http://localhost:5173/assistant-gazelle-v5/"
echo "   Backend:  http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: visible dans ce terminal"
echo ""
echo "🛑 Pour arrêter:"
echo "   Ctrl+C dans ce terminal, puis:"
echo "   kill $BACKEND_PID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Enregistrer les PIDs pour pouvoir arrêter facilement
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# Attendre que l'utilisateur arrête
wait $FRONTEND_PID
