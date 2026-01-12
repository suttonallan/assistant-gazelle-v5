#!/bin/bash
# Test d'intégration des alertes d'humidité

echo "🧪 TEST D'INTÉGRATION - ALERTES D'HUMIDITÉ"
echo "=========================================="
echo ""

API_URL="${API_URL:-http://localhost:8000}"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

# Fonction de test
test_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=${3:-200}

    echo -n "Test: $name... "

    response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ OK${NC} (HTTP $http_code)"
        test_passed=$((test_passed + 1))
        return 0
    else
        echo -e "${RED}❌ ÉCHEC${NC} (HTTP $http_code, attendu $expected_status)"
        echo "   Réponse: $body"
        test_failed=$((test_failed + 1))
        return 1
    fi
}

echo "1️⃣  TEST DES ENDPOINTS API"
echo "----------------------------"
test_endpoint "Stats globales" "/api/humidity-alerts/stats"
test_endpoint "Alertes non résolues" "/api/humidity-alerts/unresolved"
test_endpoint "Alertes résolues" "/api/humidity-alerts/resolved"
test_endpoint "Alertes archivées" "/api/humidity-alerts/archived"
test_endpoint "Alertes institutionnelles" "/api/humidity-alerts/institutional"
echo ""

echo "2️⃣  VÉRIFICATION DES DONNÉES"
echo "----------------------------"
echo -n "Récupération stats... "
stats=$(curl -s "$API_URL/api/humidity-alerts/stats")
total=$(echo "$stats" | grep -o '"total_alerts":[0-9]*' | cut -d: -f2)
unresolved=$(echo "$stats" | grep -o '"unresolved":[0-9]*' | cut -d: -f2)
resolved=$(echo "$stats" | grep -o '"resolved":[0-9]*' | cut -d: -f2)

if [ -n "$total" ]; then
    echo -e "${GREEN}✅ OK${NC}"
    echo "   Total: $total"
    echo "   Non résolues: $unresolved"
    echo "   Résolues: $resolved"
    test_passed=$((test_passed + 1))
else
    echo -e "${RED}❌ ÉCHEC${NC} (Impossible de parser les stats)"
    test_failed=$((test_failed + 1))
fi
echo ""

echo "3️⃣  RÉSUMÉ"
echo "----------------------------"
total_tests=$((test_passed + test_failed))
echo "Tests réussis: ${GREEN}$test_passed${NC}/$total_tests"
echo "Tests échoués: ${RED}$test_failed${NC}/$total_tests"
echo ""

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 TOUS LES TESTS SONT PASSÉS!${NC}"
    echo ""
    echo "✅ L'intégration des alertes d'humidité fonctionne correctement."
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Démarre le frontend: cd frontend && npm run dev"
    echo "  2. Va sur l'onglet 'Tableau de bord'"
    echo "  3. Tu devrais voir la carte 'Alertes Maintenance Institutionnelle' si des alertes existent"
    echo ""
    exit 0
else
    echo -e "${RED}❌ CERTAINS TESTS ONT ÉCHOUÉ${NC}"
    echo ""
    echo "Actions recommandées:"
    echo "  1. Vérifie que l'API est démarrée: python api/main.py"
    echo "  2. Vérifie que le SQL a été exécuté sur Supabase (voir GUIDE_ACTIVATION_ALERTES_HUMIDITE.md)"
    echo "  3. Vérifie les logs de l'API pour plus de détails"
    echo ""
    exit 1
fi
