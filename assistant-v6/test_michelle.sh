#!/bin/bash
echo "🧪 Test recherche Michelle Sutton"
echo "=================================="

curl -X POST http://localhost:8002/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"cherche michelle sutton\"}" \
  | python3 -m json.tool
