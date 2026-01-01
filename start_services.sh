#!/bin/bash
# Script de démarrage des services après redémarrage

cd /Users/allansutton/Documents/assistant-gazelle-v5

echo "🚀 Démarrage des services Assistant Gazelle"
echo ""

# Vérifier que les ports sont libres
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 déjà utilisé, arrêt du processus..."
    pkill -f "uvicorn api.main"
    sleep 2
fi

if lsof -ti:5173 > /dev/null 2>&1; then
    echo "⚠️  Port 5173 déjà utilisé, arrêt du processus..."
    pkill -f "vite"
    sleep 2
fi

# Activer l'environnement virtuel
if [ -d "venv" ]; then
    echo "✅ Activation de l'environnement virtuel..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ Activation de l'environnement virtuel..."
    source .venv/bin/activate
else
    echo "❌ Environnement virtuel non trouvé (venv ou .venv)"
    exit 1
fi

# Vérifier les variables d'environnement
if [ ! -f ".env" ]; then
    echo "❌ Fichier .env manquant!"
    exit 1
fi

echo "✅ Variables d'environnement chargées"
echo ""

# Démarrer le backend en arrière-plan
echo "🔧 Démarrage du backend (port 8000)..."
python -m uvicorn api.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
sleep 3

# Vérifier que le backend est démarré
if ! lsof -ti:8000 > /dev/null 2>&1; then
    echo "❌ Échec du démarrage du backend"
    tail -20 logs/backend.log
    exit 1
fi

echo "✅ Backend démarré sur http://localhost:8000"
echo ""

# Démarrer le frontend en arrière-plan
echo "🎨 Démarrage du frontend (port 5173)..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"
cd ..
sleep 3

# Vérifier que le frontend est démarré
if ! lsof -ti:5173 > /dev/null 2>&1; then
    echo "❌ Échec du démarrage du frontend"
    tail -20 logs/frontend.log
    exit 1
fi

echo "✅ Frontend démarré sur http://localhost:5173"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Tous les services sont démarrés!"
echo ""
echo "📊 URLs:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "🔍 Debug tournées:"
echo "   file:///Users/allansutton/Documents/assistant-gazelle-v5/frontend/debug_tournees.html"
echo ""
echo "📝 Logs:"
echo "   Backend:   tail -f logs/backend.log"
echo "   Frontend:  tail -f logs/frontend.log"
echo ""
echo "🛑 Pour arrêter les services:"
echo "   pkill -f 'uvicorn api.main'"
echo "   pkill -f 'vite'"
echo ""
echo "PIDs:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
