#!/bin/bash
# Script de monitoring des imports parallèles

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║              📊 SUIVI DES IMPORTS HISTORIQUES EN COURS                    ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Compter les processus actifs
ACTIVE=$(ps aux | grep "history_recovery" | grep -v grep | wc -l | tr -d ' ')
echo "🔥 Imports actifs: $ACTIVE processus"
echo ""

# Lister les processus actifs
if [ "$ACTIVE" -gt 0 ]; then
    echo "🔄 PROCESSUS EN COURS:"
    ps aux | grep "history_recovery" | grep -v grep | awk '{
        if ($12 ~ /--start-year/) {
            year = $13
            printf "   • Année %s (PID: %s, CPU: %s%%, Mem: %s%%)\n", year, $2, $3, $4
        }
    }'
    echo ""
fi

# Vérifier chaque année dans les logs
echo "📊 RÉSULTATS DES IMPORTS:"
for year in 2023 2022 2021 2020 2019 2018 2017 2016; do
    LOG_FILE="recovery_${year}_bg.log"
    
    if [ -f "$LOG_FILE" ]; then
        # Chercher la ligne de fin
        RESULT=$(tail -50 "$LOG_FILE" 2>/dev/null | grep "✅ Année $year")
        
        if [ ! -z "$RESULT" ]; then
            ENTRIES=$(echo "$RESULT" | grep -oE '[0-9]+ entrées importées' | grep -oE '[0-9]+')
            echo "   ✅ $year: $ENTRIES entrées importées"
        else
            # Chercher la progression
            PROGRESS=$(tail -20 "$LOG_FILE" 2>/dev/null | grep "Batch.*/" | tail -1 | sed 's/^[[:space:]]*//')
            if [ ! -z "$PROGRESS" ]; then
                echo "   🔄 $year: $PROGRESS"
            fi
        fi
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "💡 Relancer: bash scripts/monitor_imports.sh"
echo "💡 Détails: tail -30 recovery_2021_bg.log (remplacer par l'année)"
