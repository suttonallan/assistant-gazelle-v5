#!/bin/bash
# Test de l'API v6

echo "🧪 Test API v6 - Historique Monique Hallé"
echo "========================================="

curl -X POST http://localhost:8002/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"montre-moi l'historique complet de Monique Hallé\"}" \
  | python3 -m json.tool
