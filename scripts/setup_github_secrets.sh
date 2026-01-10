#!/bin/bash

# ================================================================
# Script d'injection automatique des secrets GitHub
# ================================================================
# Ce script utilise la GitHub CLI (gh) pour injecter les secrets
# nécessaires au workflow GitHub Actions de synchronisation
# ================================================================

echo "🔐 Configuration des secrets GitHub pour assistant-gazelle-v5"
echo ""

# Vérifier que gh est installé
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) n'est pas installé"
    echo ""
    echo "Installation:"
    echo "  brew install gh"
    echo ""
    echo "Puis authentification:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

# Vérifier l'authentification
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI n'est pas authentifié"
    echo ""
    echo "Authentifiez-vous avec:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

echo "✅ GitHub CLI installé et authentifié"
echo ""
echo "📋 Injection des 5 secrets dans le repository..."
echo ""

# Secret 1: SUPABASE_URL
echo "1/5 - Injection de SUPABASE_URL..."
echo "https://beblgzvmjqkcillmcavk.supabase.co" | gh secret set SUPABASE_URL

# Secret 2: SUPABASE_SERVICE_ROLE_KEY
echo "2/5 - Injection de SUPABASE_SERVICE_ROLE_KEY..."
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJlYmxnenZtanFrY2lsbG1jYXZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTkwMDY5MywiZXhwIjoyMDc1NDc2NjkzfQ.zk0ZTKueJj7GGzxy5u6agFBuKrsEJXE-5kqDD6xp-8g" | gh secret set SUPABASE_SERVICE_ROLE_KEY

# Secret 3: GAZELLE_CLIENT_ID
echo "3/5 - Injection de GAZELLE_CLIENT_ID..."
echo "yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE" | gh secret set GAZELLE_CLIENT_ID

# Secret 4: GAZELLE_CLIENT_SECRET
echo "4/5 - Injection de GAZELLE_CLIENT_SECRET..."
echo "CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc" | gh secret set GAZELLE_CLIENT_SECRET

# Secret 5: OPENAI_API_KEY (pour alertes humidité)
echo "5/5 - Injection de OPENAI_API_KEY..."
if [ -f .env ]; then
    OPENAI_KEY=$(grep "^OPENAI_API_KEY=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$OPENAI_KEY" ]; then
        echo "$OPENAI_KEY" | gh secret set OPENAI_API_KEY
        echo "✅ OPENAI_API_KEY injecté depuis .env"
    else
        echo "⚠️  OPENAI_API_KEY introuvable dans .env - skip"
    fi
else
    echo "⚠️  Fichier .env introuvable - OPENAI_API_KEY non injecté"
    echo "   (Requis pour scan alertes humidité)"
fi

echo ""
echo "✅ Tous les secrets ont été injectés avec succès!"
echo ""
echo "📊 Vérification des secrets configurés:"
gh secret list

echo ""
echo "🎯 Prochaines étapes:"
echo "1. Va sur GitHub → Actions → Timeline Incremental Sync"
echo "2. Clique sur 'Run workflow' pour lancer un test manuel"
echo "3. Vérifie les logs dans ton Dashboard → Notifications → Tâches & Imports"
echo ""
