#!/bin/bash
# Script pour guider la migration de la table users vers Gazelle IDs

echo "════════════════════════════════════════════════════════════════"
echo "  MIGRATION TABLE USERS → GAZELLE IDS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Ce script va vous guider pour migrer la table users."
echo ""
echo "📋 ÉTAPES:"
echo "  1. Copier le SQL de migration"
echo "  2. Ouvrir Supabase SQL Editor"
echo "  3. Coller et exécuter le SQL"
echo "  4. Tester la synchronisation des users"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Afficher le chemin du fichier SQL
SQL_FILE="scripts/migration_users_gazelle_ids.sql"

if [ ! -f "$SQL_FILE" ]; then
    echo "❌ Fichier SQL introuvable: $SQL_FILE"
    exit 1
fi

echo "📄 Fichier SQL: $SQL_FILE"
echo ""
echo "1️⃣  Copier le contenu du fichier SQL:"
echo ""
echo "   cat $SQL_FILE | pbcopy"
echo ""
echo "   (Le SQL est maintenant dans votre clipboard)"
echo ""

# Copier dans le clipboard si possible
if command -v pbcopy &> /dev/null; then
    cat "$SQL_FILE" | pbcopy
    echo "✅ SQL copié dans le clipboard!"
else
    echo "⚠️  pbcopy non disponible. Copiez manuellement le contenu de:"
    echo "   $SQL_FILE"
fi

echo ""
echo "2️⃣  Ouvrir Supabase SQL Editor:"
echo ""

# Extraire l'URL Supabase depuis .env
if [ -f .env ]; then
    SUPABASE_URL=$(grep SUPABASE_URL .env | cut -d '=' -f2- | tr -d '"' | tr -d ' ')
    PROJECT_ID=$(echo $SUPABASE_URL | sed 's|https://||' | cut -d '.' -f1)

    if [ ! -z "$PROJECT_ID" ]; then
        SQL_EDITOR_URL="https://supabase.com/dashboard/project/$PROJECT_ID/sql/new"
        echo "   $SQL_EDITOR_URL"
        echo ""

        # Ouvrir dans le navigateur si possible
        if command -v open &> /dev/null; then
            read -p "   Ouvrir automatiquement? (o/n): " choice
            if [ "$choice" = "o" ] || [ "$choice" = "O" ]; then
                open "$SQL_EDITOR_URL"
                echo "   ✅ Navigateur ouvert"
            fi
        fi
    fi
fi

echo ""
echo "3️⃣  Dans Supabase SQL Editor:"
echo "   - Coller le SQL (Cmd+V)"
echo "   - Cliquer sur 'Run' (ou Cmd+Enter)"
echo "   - Vérifier que tout s'exécute sans erreur"
echo ""
echo "4️⃣  Revenir ici et tester:"
echo ""
echo "   python3 test_sync_users.py"
echo ""
echo "════════════════════════════════════════════════════════════════"
