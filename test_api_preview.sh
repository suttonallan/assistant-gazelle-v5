#!/bin/bash
# Test de l'API /preview avec le format naturel d'Annie Jenkins

curl -X POST "http://localhost:8000/place-des-arts/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Est-ce possible pour vous de faire un accord du Steinway 9'\'' D - New York à 442 de la Salle D le 20 janvier entre 8h00 et 9h00?\n\nMerci de me confirmer si c'\''est possible.\n\nANNIE JENKINS",
    "source": "email"
  }' | python3 -m json.tool
