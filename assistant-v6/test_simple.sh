#!/bin/bash
curl -X POST http://localhost:8002/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"cherche michelle\"}"
