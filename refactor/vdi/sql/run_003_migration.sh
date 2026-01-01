#!/bin/bash

# Script pour exécuter la migration 003 - Table de jonction tournee_pianos
# Usage: ./run_003_migration.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/003_create_tournee_pianos_junction.sql"

echo "=========================================="
echo "Migration 003: Table de jonction tournee_pianos"
echo "=========================================="
echo ""
echo "Cette migration va:"
echo "  1. Créer la table tournee_pianos (relation piano-tournée)"
echo "  2. Migrer les données depuis JSONB piano_ids"
echo "  3. Ajouter index et RLS policies"
echo ""
echo "⚠️  La colonne piano_ids sera CONSERVÉE pour rollback"
echo "    (peut être supprimée manuellement après validation)"
echo ""

# Vérifier que le fichier SQL existe
if [ ! -f "$SQL_FILE" ]; then
  echo "❌ Erreur: Fichier $SQL_FILE introuvable"
  exit 1
fi

# Charger les variables d'environnement depuis .env
if [ -f "$SCRIPT_DIR/../../.env" ]; then
  echo "📁 Chargement .env..."
  export $(cat "$SCRIPT_DIR/../../.env" | grep -v '^#' | xargs)
fi

# Vérifier que SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont définis
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  echo "❌ Erreur: SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis dans .env"
  exit 1
fi

echo "🔗 Supabase URL: $SUPABASE_URL"
echo ""

# Extraire l'ID du projet depuis l'URL
PROJECT_ID=$(echo "$SUPABASE_URL" | sed -n 's/.*https:\/\/\([^.]*\).*/\1/p')

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Erreur: Impossible d'extraire le PROJECT_ID depuis SUPABASE_URL"
  exit 1
fi

echo "🔑 Project ID: $PROJECT_ID"
echo ""

# Vérifier la connexion DB
if [ -z "$DATABASE_URL" ]; then
  echo "⚠️  DATABASE_URL non définie dans .env"
  echo ""
  echo "Deux options pour exécuter cette migration:"
  echo ""
  echo "Option 1 - Via Supabase Dashboard:"
  echo "  1. Aller sur https://supabase.com/dashboard/project/$PROJECT_ID/sql/new"
  echo "  2. Copier-coller le contenu de:"
  echo "     $SQL_FILE"
  echo "  3. Cliquer 'Run'"
  echo ""
  echo "Option 2 - Via psql (si vous avez la connexion DB):"
  echo "  1. Ajouter DATABASE_URL dans .env"
  echo "  2. Relancer ce script"
  echo ""
  exit 0
fi

echo "▶️  Exécution de la migration via psql..."
echo ""

# Exécuter via psql
psql "$DATABASE_URL" -f "$SQL_FILE"

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Erreur lors de l'exécution"
  exit 1
fi

echo "✅ Migration 003 exécutée avec succès!"
echo ""
echo "Prochaines étapes:"
echo "  1. Tester l'ajout/retrait de pianos aux tournées"
echo "  2. Vérifier que les données ont été migrées correctement"
echo "  3. Si tout fonctionne, décommenter la ligne dans SQL pour supprimer piano_ids"
echo ""
