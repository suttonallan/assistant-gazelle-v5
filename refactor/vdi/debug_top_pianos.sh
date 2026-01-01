#!/bin/bash
# Debug script pour vérifier les pianos Top dans les tournées

echo "=== PIANOS TOP DANS TOUTES LES TOURNÉES ==="
curl -s "https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/tournee_pianos?select=tournee_id,gazelle_id,is_top&is_top=eq.true" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" | jq '.'

echo ""
echo "=== TOUS LES PIANOS DANS TOURNÉE TEST2 ==="
# Trouver l'ID de Test2
TEST2_ID=$(curl -s "https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/tournees?select=id,nom&nom=ilike.%test2%" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" | jq -r '.[0].id')

echo "ID de Test2: $TEST2_ID"
echo ""

if [ -n "$TEST2_ID" ] && [ "$TEST2_ID" != "null" ]; then
  curl -s "https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/tournee_pianos?select=gazelle_id,is_top,ordre&tournee_id=eq.${TEST2_ID}" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" | jq '.'
else
  echo "❌ Tournée Test2 non trouvée"
fi

echo ""
echo "=== TOUS LES PIANOS DANS TOURNÉE HIVER 2025 ==="
HIVER_ID="tournee_1767185054"
curl -s "https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/tournee_pianos?select=gazelle_id,is_top,ordre&tournee_id=eq.${HIVER_ID}" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" | jq '.'
