# ⚡ Quick Reference - Assistant Gazelle V5

**Cheat sheet pour les opérations quotidiennes**

---

## 🔐 Tokens

### Voir le token actuel
```python
python3 -c "from core.supabase_storage import SupabaseStorage; s=SupabaseStorage(); print(s.get_system_setting('gazelle_oauth_token')['access_token'][:30])"
```

### Injecter un nouveau token
```python
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
storage = SupabaseStorage()
storage.save_system_setting('gazelle_oauth_token', {
    "access_token": "NOUVEAU_TOKEN_ICI",
    "refresh_token": "manual_override",
    "expires_at": 1999999999,
    "created_at": 0
})
print("✅ Token injecté")
EOF
```

---

## 🚀 Démarrage

### API Backend
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5/frontend
npm run dev
# → http://localhost:5174
```

### Redémarrer tout proprement
```bash
# Tuer les processus
pkill -f "uvicorn.*main:app"
pkill -f "vite"

# Relancer
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npm run dev &
```

---

## 🔍 Tests Rapides

### Tester l'API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/institutions/list | python3 -m json.tool
curl http://localhost:8000/vincent-dindy/pianos | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Pianos: {d['count']}\")"
```

### Tester Supabase
```python
python3 -c "from core.supabase_storage import SupabaseStorage; s=SupabaseStorage(); print('✅ Supabase OK')"
```

### Tester API Gazelle
```python
python3 << 'EOF'
from core.gazelle_api_client import GazelleAPIClient
client = GazelleAPIClient()
result = client._execute_query('query { allClients { nodes { id companyName } } }')
print(f"✅ API Gazelle OK - {len(result['data']['allClients']['nodes'])} clients")
EOF
```

---

## 🗄️ Requêtes SQL Utiles

### Tags institutionnels
```sql
SELECT external_id, company_name, tags
FROM gazelle_clients
WHERE tags && ARRAY['institutional'];
```

### Pianos avec PLS
```sql
SELECT COUNT(*), make
FROM gazelle_pianos
WHERE dampp_chaser_installed = true
GROUP BY make;
```

### Alertes actives
```sql
SELECT client_name, piano_make, alert_type, observed_at
FROM humidity_alerts_active
WHERE is_resolved = false
ORDER BY observed_at DESC
LIMIT 10;
```

### Institutions configurées
```sql
SELECT slug, name, gazelle_client_id, active
FROM institutions;
```

### Token système
```sql
SELECT key, value->>'access_token' as token_preview
FROM system_settings
WHERE key = 'gazelle_oauth_token';
```

---

## 🛠️ Scripts Utiles

### Sync Gazelle → Supabase
```bash
python3 scripts/sync_to_supabase.py
```

### Détecter PLS (Badge Dampp-Chaser)
```bash
python3 scripts/detect_dampp_chaser_installations.py --write
```

### Générer Rapport Timeline
```python
python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"
```

### Rafraîchir Token OAuth
```bash
python3 scripts/auto_refresh_token.py --force
```

---

## 🐛 Debugging

### Voir les logs API
```bash
ls -t logs/api_*.log | head -1 | xargs tail -100
```

### Erreurs dans les logs
```bash
grep -i "error\|exception\|401\|500" logs/api_*.log | tail -30
```

### Processus en cours
```bash
ps aux | grep -E "(uvicorn|vite|python.*api)" | grep -v grep
```

### Ports utilisés
```bash
lsof -ti:8000  # API
lsof -ti:5174  # Frontend
```

---

## 🔧 Fixes Rapides

### Token expiré (401)
```bash
# 1. Récupérer nouveau token depuis navigateur (F12 > Network > Headers > x-gazelle-api-key)
# 2. Injecter (voir section Tokens ci-dessus)
# 3. Redémarrer API
pkill -f "uvicorn.*main:app"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
```

### Badge PLS disparu
```bash
nohup python3 scripts/detect_dampp_chaser_installations.py --write \
  > logs/detect_pls_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### Tags institutionnels perdus
```python
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
storage = SupabaseStorage()

institutions = [
    ('cli_9UMLkteep8EsISbG', 'Vincent-d\'Indy'),
    ('cli_HbEwl9rN11pSuDEU', 'Place des Arts'),
    ('cli_sos6RK8t4htOApiM', 'UQAM'),
    ('cli_UVMjT9g1b1wDkRHr', 'SMCQ'),
    ('cli_xkMYNQrSX7T7E1q0', 'Fondation Vincent-d\'Indy'),
]

for client_id, name in institutions:
    storage.client.table('gazelle_clients').update({
        'tags': ['institutional']
    }).eq('external_id', client_id).execute()
    print(f"✅ {name}")
EOF
```

### Port déjà utilisé
```bash
# API (8000)
lsof -ti:8000 | xargs kill

# Frontend (5174)
pkill -f "vite"
```

---

## 📊 IDs Critiques

### Clients Institutionnels (3 INSTITUTIONS)
```
cli_9UMLkteep8EsISbG  → École de musique Vincent-d'Indy (121 pianos)
cli_HbEwl9rN11pSuDEU  → Place des Arts (16 pianos)
cli_PmqPUBTbPFeCMGmz  → Orford Musique (61 pianos)
```

### Slugs Institutions
```
vincent-dindy   → École de musique Vincent-d'Indy
place-des-arts  → Place des Arts
orford          → Orford Musique
```

---

## 📝 Ajouter une Institution

### 1. Ajouter dans Supabase
```sql
INSERT INTO institutions (slug, name, gazelle_client_id, active)
VALUES ('nouvelle-ecole', 'Nouvelle École', 'cli_xxxxx', true);
```

### 2. Assigner le tag 'institutional' au client
```sql
UPDATE gazelle_clients
SET tags = ARRAY['institutional']
WHERE external_id = 'cli_xxxxx';
```

### 3. Ajouter dans l'API humidity_alerts si surveillance nécessaire
Éditer `/api/humidity_alerts_routes.py` ligne 62:
```python
INSTITUTIONAL_CLIENT_IDS = [
    'cli_9UMLkteep8EsISbG',
    'cli_HbEwl9rN11pSuDEU',
    'cli_PmqPUBTbPFeCMGmz',
    'cli_sos6RK8t4htOApiM',
    'cli_UVMjT9g1b1wDkRHr',
    'cli_xxxxx',  # ← Nouvelle institution
]
```

### 4. Tester
```bash
curl http://localhost:8000/institutions/list | python3 -m json.tool
curl http://localhost:8000/nouvelle-ecole/pianos | python3 -m json.tool
```

---

## 🔄 Workflow Quotidien

### Matin (5 min)
1. Démarrer API + Frontend
2. Vérifier token : `python3 scripts/auto_refresh_token.py`
3. Vérifier logs : `tail -50 logs/api_*.log`

### Après sync Gazelle (10 min)
1. Sync : `python3 scripts/sync_to_supabase.py`
2. Détecter PLS : `python3 scripts/detect_dampp_chaser_installations.py --write`
3. Vérifier tags : `SELECT COUNT(*) FROM gazelle_clients WHERE tags && ARRAY['institutional']`

### Fin de journée (2 min)
1. Générer rapport : `python3 -c "from modules.reports.service_reports import generate_reports; generate_reports()"`
2. Backup logs : `cp logs/api_*.log backups/`

---

## 📚 Documentation Complète

- **Architecture complète :** `/docs/ARCHITECTURE_GUIDE.md` ← Tout est là !
- **Rapport Timeline :** `/v6/RAPPORT_TIMELINE_V5_RECETTE.md`
- **Post-mortem incidents :** `/v6/INCIDENT_*.md`
- **Setup Google :** `/docs/SETUP_GOOGLE_CREDENTIALS.md`

---

**Mis à jour :** 2026-01-20  
**Version :** 1.0
