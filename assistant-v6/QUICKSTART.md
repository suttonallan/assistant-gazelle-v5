# Guide de Démarrage Rapide - Assistant v6

## 🚀 Démarrage en 3 étapes

### 1. Démarrer le serveur v6 (port 8001)

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/api
python3 assistant_v6.py
```

Le serveur démarre sur **http://localhost:8001**

**Note**: Le serveur charge automatiquement les variables d'environnement depuis `../.env` avec `python-dotenv`. Si le `.env` manque ou si `SUPABASE_URL`/`SUPABASE_KEY` ne sont pas définis, le programme s'arrête immédiatement avec un message d'erreur clair.

### 2. Tester directement dans le terminal

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/modules/assistant/services
python queries_v6.py
```

Cela lance les tests automatiques avec les questions prédéfinies.

### 3. Tests A/B (v5 vs v6)

**Prérequis**: v5 doit tourner sur port 8000, v6 sur port 8001

```bash
# Terminal 1: Démarrer v5 (déjà running normalement)
cd /Users/allansutton/Documents/assistant-gazelle-v5
uvicorn api.main:app --reload --port 8000

# Terminal 2: Démarrer v6
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/api
python assistant_v6.py

# Terminal 3: Lancer les tests A/B
cd /Users/allansutton/Documents/assistant-gazelle-v5/assistant-v6/tests
python test_ab_comparison.py
```

## 📊 Tester avec curl

### v6 - Historique de service
```bash
curl -X POST http://localhost:8001/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "montre-moi l'\''historique complet de Monique Hallé avec toutes les notes de service"}'
```

### v6 - Recherche client
```bash
curl -X POST http://localhost:8001/v6/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "trouve Michelle Alie"}'
```

### v6 - Health check
```bash
curl http://localhost:8001/v6/assistant/health
```

## 🧪 Questions de test recommandées

### Timeline (Historique)
- "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service"
- "historique de Jean-Philippe Gagné"
- "affiche l'historique de Michelle Alie"

### Search Client
- "trouve Michelle Alie"
- "cherche Allan Sutton"
- "recherche Monique Hallé"

### Appointments (En développement)
- "mes rv demain"
- "calendrier de Nick cette semaine"

## 📈 Comprendre les résultats

### Format de réponse Timeline
```json
{
  "response": "📜 Historique de Monique Hallé\n\n🎹 2 pianos trouvés\n📊 153 événements...",
  "data": {
    "type": "timeline",
    "client_name": "Monique Hallé",
    "client_id": "cli_xxx",
    "piano_count": 2,
    "piano_ids": ["pia_xxx", "pia_yyy"],
    "count": 153,
    "total": 200,
    "entries": [...]
  },
  "version": "v6"
}
```

### Format de réponse Search
```json
{
  "response": "🔍 2 clients trouvés:\n\n- Michelle Alie (Client, ID: cli_xxx)\n...",
  "data": {
    "type": "search_client",
    "count": 2,
    "clients": [...]
  },
  "version": "v6"
}
```

## 🔧 Debugging

### Voir les logs détaillés

Le mode debug est activé par défaut. Vous verrez:
- 🔍 Parser: détection de type
- 🎹 Recherche de pianos
- 📊 Comptage des entrées timeline
- ✅ Déduplication des clients

### Problèmes courants

**"Serveur non accessible"**
→ Vérifiez que le serveur v6 tourne sur port 8001

**"SUPABASE_URL non défini"**
→ Vérifiez que le fichier `.env` contient SUPABASE_URL et SUPABASE_KEY

**"Aucun client trouvé"**
→ Vérifiez l'orthographe du nom (fuzzy matching actif)

## 🎯 Différences clés v5 vs v6

| Aspect | v5 | v6 |
|--------|----|----|
| **Architecture** | Itérative, complexe | Propre, 4 piliers |
| **Timeline** | Cherche client seulement | Client + tous ses pianos |
| **Parser** | Règles ambiguës | Priorités claires |
| **Déduplication** | Basée sur ID | Basée sur nom normalisé |
| **Code** | Dispersé sur plusieurs modules | Centralisé, lisible |

## 📝 Prochaines étapes

- [ ] Implémenter APPOINTMENTS (rendez-vous futurs)
- [ ] Implémenter CLIENT_INFO (informations paiement)
- [ ] Implémenter DEDUCTIONS (recommandations basées sur piano attributes)
- [ ] Intégrer v6 dans le frontend
- [ ] Migration complète v5 → v6
