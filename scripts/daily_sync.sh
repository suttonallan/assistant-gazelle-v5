#!/bin/bash
# Script de synchronisation quotidienne Gazelle → Supabase
# Exécuté automatiquement chaque jour pour maintenir les données à jour

# Se placer dans le répertoire du projet
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Log file avec date
LOG_DIR="/Users/allansutton/Documents/assistant-gazelle-v5/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sync-$(date +%Y-%m-%d).log"

# Exécuter la synchronisation
echo "========================================" >> "$LOG_FILE"
echo "Sync démarré: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

/usr/bin/python3 modules/sync_gazelle/sync_to_supabase.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

echo "========================================" >> "$LOG_FILE"
echo "Sync terminé: $(date) (exit code: $EXIT_CODE)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Garder seulement les logs des 7 derniers jours
find "$LOG_DIR" -name "sync-*.log" -mtime +7 -delete

exit $EXIT_CODE
